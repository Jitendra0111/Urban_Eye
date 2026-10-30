"""Satellite endpoints: imagery dates for a place, analysis of a map area, change between dates.
Results are saved to the database and reused for identical requests (see db.py)."""
import logging

import httpx
import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from . import db
from .config import settings
from .models import registry
from .routes import (coverage_of, detect_result, impact_result, require_segmenter,
                     segment_result)
from .schemas import (CompareRequest, CompareResponse, Release, SatelliteAnalysisResponse,
                      SatelliteRequest, Scene)
from .services import satellite as sat
from .services import segmenter as seg
from .services.change import compare
from .services.images import to_data_url

router = APIRouter(prefix="/api/satellite", tags=["satellite"])
log = logging.getLogger(__name__)


def _client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


async def _fetch(request: Request, bbox: list[float], release: int | None, zoom: int | None) -> dict:
    try:
        bbox = list(sat.validate_bbox(bbox))
        z = zoom or sat.choose_zoom(bbox, settings.satellite_max_pixels, settings.satellite_zoom)
        w, h = sat.pixel_size(bbox, z)
        if w * h > settings.satellite_max_pixels:
            raise sat.SatelliteError("Area too large for this zoom. Select a smaller area or a lower zoom.")
        if w < 64 or h < 64:
            raise sat.SatelliteError("Area too small. Select at least about 50 × 50 m.")
        scene = await sat.fetch_image(_client(request), bbox, z, release)
    except sat.SatelliteError as e:
        raise HTTPException(422, str(e))
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Could not download satellite imagery: {e}")
    scene["date"] = await _release_date(request, scene["release"])
    return scene


async def _release_date(request: Request, release: int | None) -> str:
    if release is None:
        return "latest"
    try:
        for r in await sat.list_releases(_client(request)):
            if r["release"] == release:
                return r["date"]
    except httpx.HTTPError:
        pass
    return "unknown"


def _scene_model(scene: dict) -> Scene:
    rgb = scene["rgb"]
    return Scene(image=to_data_url(rgb), width=rgb.shape[1], height=rgb.shape[0], zoom=scene["zoom"],
                 meters_per_pixel=round(scene["meters_per_pixel"], 3),
                 area_ha=round(scene["area_ha"], 2), release=scene["release"], date=scene["date"],
                 attribution=sat.ATTRIBUTION)


def _analyze(scene: dict, detect: bool, labels: np.ndarray | None = None) -> SatelliteAnalysisResponse:
    rgb = scene["rgb"]
    if registry.segmenter is not None:
        if labels is None:
            labels = registry.segmenter.predict(rgb)
        segmentation = segment_result(rgb, labels)
        impact = impact_result("segmentation", segmentation.coverage)
    else:
        segmentation = None
        impact = impact_result(*coverage_of(rgb))
    detection = detect_result(rgb, 0.25) if detect and registry.detector else None
    return SatelliteAnalysisResponse(scene=_scene_model(scene), segmentation=segmentation,
                                     impact=impact, detection=detection)


# ---------------------------------------------------------------- database: cache and history

def _model_tag(detect: bool = False) -> str:
    """Identifies the models behind a result, so a new model never reuses an old model's results."""
    tag = registry.segmenter.name if registry.segmenter is not None else "no segmentation model"
    if detect and registry.detector is not None:
        tag += f" + {registry.detector.name}"
    return tag


def _cached(key: str, uses_latest: bool, model_cls: type[BaseModel]) -> BaseModel | None:
    try:
        rec = db.find_cached(key, uses_latest)
        if rec is None:
            return None
        return model_cls.model_validate(db.load_result(rec)).model_copy(
            update={"saved_id": rec.id, "cached": True})
    except (SQLAlchemyError, ValueError) as e:
        log.warning("Could not read a saved result, running the model instead: %s", e)
        return None


def _save(kind: str, key: str, bbox: list[float], result: BaseModel, summary: dict) -> BaseModel:
    """Save the result; a database problem never breaks the response, it only skips saving."""
    try:
        record_id = db.save(kind, key, bbox, summary,
                            result.model_dump_json(exclude={"saved_id", "cached"}))
        return result.model_copy(update={"saved_id": record_id})
    except SQLAlchemyError as e:
        log.warning("Could not save the result: %s", e)
        return result


def _summary(res: SatelliteAnalysisResponse) -> dict:
    return {"area_ha": res.scene.area_ha, "release": res.scene.release, "date": res.scene.date,
            "coverage": res.impact.coverage, "green_score": res.impact.green_score,
            "urban_score": res.impact.urban_score, "level": res.impact.level}


# ---------------------------------------------------------------- endpoints

@router.get("/dates", response_model=list[Release],
            summary="Dates with distinct imagery at a location (newest first)")
async def dates(request: Request, lat: float = Query(..., ge=-85, le=85),
                lon: float = Query(..., ge=-180, le=180)):
    try:
        # Checked at the analysis zoom, so every listed date can actually be analysed.
        return await sat.available_dates(_client(request), lat, lon, settings.satellite_zoom)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Could not reach the imagery archive: {e}")


@router.post("/analyze", response_model=SatelliteAnalysisResponse,
             summary="Download the satellite image for an area and analyse its land cover")
async def analyze(request: Request, body: SatelliteRequest):
    key = db.cache_key(kind="analysis", bbox=body.bbox, zoom=body.zoom, release=body.release,
                       detect=body.detect, model=_model_tag(body.detect))
    if not body.refresh:
        hit = await run_in_threadpool(_cached, key, body.release is None, SatelliteAnalysisResponse)
        if hit is not None:
            return hit
    scene = await _fetch(request, body.bbox, body.release, body.zoom)

    def work():
        result = _analyze(scene, body.detect)
        return _save("analysis", key, list(body.bbox), result,
                     {**_summary(result), "model": _model_tag(body.detect)})

    return await run_in_threadpool(work)


@router.post("/compare", response_model=CompareResponse,
             summary="Land-cover change in an area between two imagery dates")
async def compare_dates(request: Request, body: CompareRequest):
    model = require_segmenter()
    bbox = list(body.bbox)
    key = db.cache_key(kind="comparison", bbox=bbox, zoom=body.zoom, release=body.release_before,
                       release_after=body.release_after, model=_model_tag())
    if not body.refresh:
        hit = await run_in_threadpool(_cached, key, body.release_after is None, CompareResponse)
        if hit is not None:
            return hit
    try:
        zoom = body.zoom or sat.choose_zoom(sat.validate_bbox(bbox), settings.satellite_max_pixels,
                                            settings.satellite_zoom)
    except sat.SatelliteError as e:
        raise HTTPException(422, str(e))
    before = await _fetch(request, bbox, body.release_before, zoom)
    after = await _fetch(request, bbox, body.release_after, zoom)

    def work():
        lb, la = model.predict(before["rgb"]), model.predict(after["rgb"])
        res_b, res_a = _analyze(before, False, lb), _analyze(after, False, la)
        diff = compare(lb, la, after["rgb"], after["area_ha"])
        cov_change = {c: round(res_a.segmentation.coverage[c] - res_b.segmentation.coverage[c], 2)
                      for c in seg.CLASS_NAMES}
        result = CompareResponse(before=res_b, after=res_a, changed_percent=diff["changed_percent"],
                                 changed_hectares=diff["changed_hectares"], coverage_change=cov_change,
                                 transitions=diff["transitions"],
                                 change_map=to_data_url(diff["change_map"]))
        summary = {**_summary(res_a), "release": res_b.scene.release, "date": res_b.scene.date,
                   "release_after": res_a.scene.release, "date_after": res_a.scene.date,
                   "changed_percent": result.changed_percent,
                   "changed_hectares": result.changed_hectares, "model": _model_tag()}
        return _save("comparison", key, bbox, result, summary)

    return await run_in_threadpool(work)
