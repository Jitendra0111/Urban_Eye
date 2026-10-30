"""Response models (these also generate the interactive docs at /docs)."""
from pydantic import BaseModel, Field


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


class CompareRequest(BaseModel):
    bbox: list[float] = Field(min_length=4, max_length=4, description=BBOX_DOC)
    release_before: int
    release_after: int | None = Field(None, description="Empty = latest imagery")
    zoom: int | None = Field(None, ge=16, le=19)


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


class HealthResponse(BaseModel):
    status: str
    device: str
    segmentation_model: bool
    detector: str | None
