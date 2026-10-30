"""Endpoints for uploaded photos. Inference endpoints are plain `def`, so FastAPI runs them in a
worker thread and the server stays responsive while a model is running."""
import httpx
import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from sqlalchemy.exc import SQLAlchemyError

from . import db
from .config import settings
from .models import registry
from .schemas import (QUALITY_DOC, AnalysisResponse, DetectResponse, HealthResponse,
                      ImpactResponse, Quality, SegmentResponse)
from .services import detector as det
from .services import segmenter as seg
from .services.images import InvalidImage, decode_image, to_data_url
from .services.impact import calculate_impact

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------- shared helpers

def read_upload(file: UploadFile) -> np.ndarray:
    data = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image larger than {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(400, "Empty file")
    try:
        return decode_image(data)
    except InvalidImage as e:
        raise HTTPException(415, str(e))


def run_detector(rgb: np.ndarray, confidence: float):
    if registry.detector is None:
        raise HTTPException(503, "No detection model configured (see backend README)")
    try:
        return registry.detector.detect(rgb, confidence)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Roboflow request failed: {e}")


def require_segmenter():
    if registry.segmenter is None:
        raise HTTPException(503, "Segmentation model not loaded: put unetpp_oem8_best.pth in "
                                 "backend/models (see backend README)")
    return registry.segmenter


def segment_result(rgb: np.ndarray, labels: np.ndarray) -> SegmentResponse:
    return SegmentResponse(model=registry.segmenter.name, image_width=rgb.shape[1],
                           image_height=rgb.shape[0], coverage=seg.coverage(labels),
                           legend=seg.legend(), mask_image=to_data_url(seg.colorize(labels)),
                           overlay_image=to_data_url(seg.overlay(rgb, labels)))


def detect_result(rgb: np.ndarray, confidence: float) -> DetectResponse:
    detections = run_detector(rgb, confidence)
    return DetectResponse(model=registry.detector.name, image_width=rgb.shape[1],
                          image_height=rgb.shape[0], detections=detections,
                          counts=det.counts(detections),
                          annotated_image=to_data_url(det.annotate(rgb, detections)))


def impact_result(source: str, coverage: dict[str, float]) -> ImpactResponse:
    return ImpactResponse(source=source, coverage=coverage, **calculate_impact(coverage))


def coverage_of(rgb: np.ndarray, tta: bool = True) -> tuple[str, dict[str, float]]:
    """Pixel-accurate coverage from U-Net++ when available, otherwise box area from the detector."""
    if registry.segmenter is not None:
        return "segmentation", seg.coverage(registry.segmenter.predict(rgb, tta=tta))
    detections = run_detector(rgb, 0.3)
    return "detection", det.box_coverage(detections, rgb.shape[1], rgb.shape[0])


# ---------------------------------------------------------------- endpoints

@router.get("/health", response_model=HealthResponse)
def health():
    try:
        saved = db.count()
    except SQLAlchemyError:
        saved = None
    return HealthResponse(status="ok", device=registry.device,
                          segmentation_model=registry.segmenter is not None,
                          detector=registry.detector.name if registry.detector else None,
                          saved_results=saved)


@router.get("/classes")
def classes():
    return {"segmentation": seg.legend()}


@router.post("/detect", response_model=DetectResponse,
             summary="Detect objects and return the annotated image (replaces the Gradio demo)")
def detect(file: UploadFile = File(...), confidence: float = Query(0.25, ge=0.0, le=1.0)):
    return detect_result(read_upload(file), confidence)


@router.post("/segment", response_model=SegmentResponse,
             summary="Land-cover segmentation with U-Net++ (8 OpenEarthMap classes)")
def segment(file: UploadFile = File(...), quality: Quality = Query("accurate", description=QUALITY_DOC)):
    model = require_segmenter()
    rgb = read_upload(file)
    return segment_result(rgb, model.predict(rgb, tta=quality == "accurate"))


@router.post("/analysis", response_model=AnalysisResponse,
             summary="Percent of the image covered by each class (Land Analysis page)")
def analysis(file: UploadFile = File(...), quality: Quality = Query("accurate", description=QUALITY_DOC)):
    source, cov = coverage_of(read_upload(file), tta=quality == "accurate")
    return AnalysisResponse(source=source, coverage=cov)


@router.post("/environmental-impact", response_model=ImpactResponse,
             summary="Green / urban scores, status and recommendations (Environmental Impact page)")
def environmental_impact(file: UploadFile = File(...),
                         quality: Quality = Query("accurate", description=QUALITY_DOC)):
    return impact_result(*coverage_of(read_upload(file), tta=quality == "accurate"))
