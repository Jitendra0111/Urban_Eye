"""Object detection: local YOLO11 weights (Ultralytics) or the hosted Roboflow model."""
import io
import threading
from pathlib import Path

import httpx
import numpy as np
from PIL import Image, ImageDraw

from ..schemas import Detection


class YoloDetector:
    def __init__(self, weights: Path, device: str):
        from ultralytics import YOLO

        self.model = YOLO(str(weights))
        self.device = device
        self.lock = threading.Lock()
        self.name = f"YOLO {Path(weights).name}"

    def detect(self, rgb: np.ndarray, confidence: float) -> list[Detection]:
        with self.lock:
            # Ultralytics treats numpy input as BGR
            result = self.model.predict(rgb[:, :, ::-1], conf=confidence, device=self.device,
                                        verbose=False)[0]
        names = result.names
        return [
            Detection(class_name=names[int(c)], confidence=round(float(s), 4),
                      bbox=[round(float(v), 1) for v in box])
            for box, s, c in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist(),
                                 result.boxes.cls.tolist())
        ]


class RoboflowDetector:
    """Same hosted model the Flutter app called directly; the API key now stays on the server."""

    def __init__(self, api_key: str, model_id: str):
        self.url = f"https://detect.roboflow.com/{model_id}"
        self.api_key = api_key
        self.name = f"Roboflow {model_id}"

    def detect(self, rgb: np.ndarray, confidence: float) -> list[Detection]:
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, format="JPEG", quality=95)
        resp = httpx.post(self.url, params={"api_key": self.api_key, "confidence": confidence,
                                            "format": "json"},
                          files={"file": ("image.jpg", buf.getvalue(), "image/jpeg")}, timeout=60)
        resp.raise_for_status()
        detections = []
        for p in resp.json().get("predictions", []):
            x, y, w, h = p["x"], p["y"], p["width"], p["height"]     # Roboflow boxes are centre-based
            detections.append(Detection(class_name=str(p["class"]),
                                        confidence=round(float(p["confidence"]), 4),
                                        bbox=[x - w / 2, y - h / 2, x + w / 2, y + h / 2]))
        return detections


def counts(detections: list[Detection]) -> dict[str, int]:
    out: dict[str, int] = {}
    for d in detections:
        out[d.class_name] = out.get(d.class_name, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def box_coverage(detections: list[Detection], width: int, height: int) -> dict[str, float]:
    """Percent of the image covered by each class's boxes. Overlapping boxes are counted once,
    so values never exceed 100% (the old Flutter code summed box areas)."""
    masks: dict[str, np.ndarray] = {}
    for d in detections:
        x1, y1, x2, y2 = (int(round(v)) for v in d.bbox)
        m = masks.setdefault(d.class_name.lower(), np.zeros((height, width), dtype=bool))
        m[max(0, y1):max(0, y2), max(0, x1):max(0, x2)] = True
    total = width * height
    return {cls: round(float(m.sum()) * 100 / total, 2) for cls, m in masks.items()}


def annotate(rgb: np.ndarray, detections: list[Detection]) -> np.ndarray:
    img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(img)
    for d in detections:
        color = _color(d.class_name)
        draw.rectangle(d.bbox, outline=color, width=max(2, img.width // 400))
        label = f"{d.class_name} {d.confidence:.2f}"
        x1, y1 = d.bbox[0], d.bbox[1]
        tw, th = draw.textbbox((0, 0), label)[2:]
        draw.rectangle([x1, y1 - th - 4, x1 + tw + 4, y1], fill=color)
        draw.text((x1 + 2, y1 - th - 2), label, fill="white")
    return np.asarray(img)


def _color(name: str) -> tuple[int, int, int]:
    h = sum(ord(ch) * 31 ** i for i, ch in enumerate(name)) % 360
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h / 360, 0.75, 0.85)
    return int(r * 255), int(g * 255), int(b * 255)
