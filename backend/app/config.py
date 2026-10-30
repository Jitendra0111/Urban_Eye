"""Settings read from environment variables (or a .env file in the backend folder)."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _path(name: str, default: str) -> Path:
    p = Path(os.getenv(name, default))
    return p if p.is_absolute() else BACKEND_DIR / p


def _list(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    # U-Net++ (EfficientNet-B4) trained on the 8 OpenEarthMap classes -> best.pth from the Colab notebook
    seg_weights: Path = field(default_factory=lambda: _path("SEG_WEIGHTS", "models/unetpp_oem8_best.pth"))
    seg_encoder: str = os.getenv("SEG_ENCODER", "efficientnet-b4")
    seg_tile: int = int(os.getenv("SEG_TILE", "1024"))

    # Object detector: "yolo" (local Ultralytics weights), "roboflow" (hosted API) or "auto"
    detector: str = os.getenv("DETECTOR", "auto").lower()
    yolo_weights: Path = field(default_factory=lambda: _path("YOLO_WEIGHTS", "models/yolo11_best.pt"))
    roboflow_api_key: str = os.getenv("ROBOFLOW_API_KEY", "")
    roboflow_model_id: str = os.getenv("ROBOFLOW_MODEL_ID", "detection-xdxfj/1")

    # Satellite imagery: zoom 18 ~ 0.5 m/pixel (close to the OpenEarthMap training resolution)
    satellite_zoom: int = int(os.getenv("SATELLITE_ZOOM", "18"))
    satellite_max_pixels: int = int(os.getenv("SATELLITE_MAX_PIXELS", str(2048 * 2048)))

    # Results database: SQLite file by default; e.g. postgresql+psycopg://user:pass@host/urbaneye
    database_url: str = os.getenv("DATABASE_URL") or f"sqlite:///{(BACKEND_DIR / 'data' / 'urbaneye.db').as_posix()}"
    cache_latest_days: int = int(os.getenv("CACHE_LATEST_DAYS", "7"))   # "latest imagery" changes over time

    device: str = os.getenv("DEVICE", "auto")          # "auto", "cpu", "cuda"
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    cors_origins: list[str] = field(default_factory=lambda: _list(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"))

    @property
    def database_path(self) -> Path:
        """SQLite file location (only meaningful for sqlite:/// URLs)."""
        return Path(self.database_url.removeprefix("sqlite:///"))


settings = Settings()
