"""Response models (these also generate the interactive docs at /docs)."""
from typing import Literal

from pydantic import BaseModel, Field

Quality = Literal["fast", "accurate"]
QUALITY_DOC = ('"accurate" averages the image and its mirror image (2 model passes); '
               '"fast" uses one pass, about half the time')


class Detection(BaseModel):
    class_name: str
    confidence: float
    bbox: list[float] = Field(description="[x1, y1, x2, y2] in pixels")


class DetectResponse(BaseModel):
    model: str
    image_width: int
    image_height: int
    detections: list[Detection]
    counts: dict[str, int]
    annotated_image: str = Field(description="PNG as a data URL, usable directly in <img src>")


class SegmentResponse(BaseModel):
    model: str
    image_width: int
    image_height: int
    coverage: dict[str, float] = Field(description="Percent of labeled pixels per class")
    legend: dict[str, str] = Field(description="Class -> hex colour used in the mask")
    mask_image: str
    overlay_image: str


class AnalysisResponse(BaseModel):
    source: str = Field(description='"segmentation" (pixel-accurate) or "detection" (box area)')
    coverage: dict[str, float]


class ImpactResponse(AnalysisResponse):
    status: str
    level: str = Field(description="healthy | balanced | warning | danger | critical | unknown")
    green_score: float
    urban_score: float
    recommendations: list[str]


BBOX_DOC = "[west, south, east, north] in degrees (WGS84)"


class SatelliteRequest(BaseModel):
    bbox: list[float] = Field(min_length=4, max_length=4, description=BBOX_DOC)
    release: int | None = Field(None, description="Wayback release id from /api/satellite/dates; "
                                                  "empty = latest imagery")
    zoom: int | None = Field(None, ge=16, le=19, description="Empty = finest zoom that fits")
    detect: bool = Field(False, description="Also run the object detector")
    quality: Quality = Field("accurate", description=QUALITY_DOC)
    refresh: bool = Field(False, description="Ignore a saved result and run the model again")


class CompareRequest(BaseModel):
    bbox: list[float] = Field(min_length=4, max_length=4, description=BBOX_DOC)
    release_before: int
    release_after: int | None = Field(None, description="Empty = latest imagery")
    zoom: int | None = Field(None, ge=16, le=19)
    quality: Quality = Field("accurate", description=QUALITY_DOC)
    refresh: bool = Field(False, description="Ignore a saved result and run the model again")


class Release(BaseModel):
    release: int
    date: str
    title: str


class Scene(BaseModel):
    image: str
    width: int
    height: int
    zoom: int
    meters_per_pixel: float
    area_ha: float
    release: int | None
    date: str = Field(description='Imagery version date, or "latest"')
    attribution: str


class SatelliteAnalysisResponse(BaseModel):
    scene: Scene
    segmentation: SegmentResponse | None
    impact: ImpactResponse
    detection: DetectResponse | None = None
    quality: Quality = "accurate"
    saved_id: int | None = Field(None, description="Id of this result in the history database")
    cached: bool = Field(False, description="True when returned from the database instead of re-run")


class Transition(BaseModel):
    from_class: str
    to_class: str
    percent: float
    hectares: float


class CompareResponse(BaseModel):
    before: SatelliteAnalysisResponse
    after: SatelliteAnalysisResponse
    changed_percent: float
    changed_hectares: float
    coverage_change: dict[str, float] = Field(description="after - before, percentage points")
    transitions: list[Transition]
    change_map: str
    quality: Quality = "accurate"
    saved_id: int | None = Field(None, description="Id of this result in the history database")
    cached: bool = Field(False, description="True when returned from the database instead of re-run")


class HealthResponse(BaseModel):
    status: str
    device: str
    segmentation_model: bool
    detector: str | None
    saved_results: int | None = Field(None, description="Results in the database (None if unavailable)")


class HistoryItem(BaseModel):
    id: int
    kind: str = Field(description='"analysis" or "comparison"')
    created_at: str
    bbox: list[float] = Field(description=BBOX_DOC)
    area_ha: float
    date: str = Field(description="Imagery date (the earlier date for comparisons)")
    date_after: str | None
    release: int | None
    release_after: int | None
    coverage: dict[str, float]
    green_score: float
    urban_score: float
    level: str
    changed_percent: float | None
    changed_hectares: float | None
    model: str


class HistoryPage(BaseModel):
    total: int
    items: list[HistoryItem]


class HistoryEntry(BaseModel):
    item: HistoryItem
    result: dict = Field(description="The saved /analyze or /compare response")
