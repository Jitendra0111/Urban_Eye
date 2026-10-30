"""API tests with stand-in models, so they run without torch or trained weights:  pytest -q"""
import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.models import registry
from app.schemas import Detection
from app.services.impact import calculate_impact


class FakeSegmenter:
    name = "fake-unet"

    def predict(self, rgb, tta=True):
        labels = np.full(rgb.shape[:2], 4, dtype=np.uint8)   # tree
        labels[: rgb.shape[0] // 4] = 7                      # top quarter building
        return labels


class FakeDetector:
    name = "fake-yolo"

    def detect(self, rgb, confidence):
        return [Detection(class_name="building", confidence=0.9, bbox=[0, 0, 50, 50]),
                Detection(class_name="building", confidence=0.8, bbox=[25, 25, 75, 75]),
                Detection(class_name="road", confidence=0.7, bbox=[0, 90, 100, 100])]


def png(w=100, h=100):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (90, 140, 60)).save(buf, format="PNG")
    return {"file": ("img.png", buf.getvalue(), "image/png")}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(registry, "load", lambda: None)
    monkeypatch.setattr(registry, "segmenter", FakeSegmenter())
    monkeypatch.setattr(registry, "detector", FakeDetector())
    with TestClient(app) as c:
        yield c


def test_health(client):
    body = client.get("/api/health").json()
    assert body["segmentation_model"] is True and body["detector"] == "fake-yolo"


def test_detect(client):
    body = client.post("/api/detect", files=png()).json()
    assert body["counts"] == {"building": 2, "road": 1}
    assert body["annotated_image"].startswith("data:image/png;base64,")


def test_segment(client):
    body = client.post("/api/segment", files=png()).json()
    assert body["coverage"]["building"] == 25.0 and body["coverage"]["tree"] == 75.0
    assert body["mask_image"].startswith("data:image/png")


def test_analysis_uses_segmentation(client):
    body = client.post("/api/analysis", files=png()).json()
    assert body["source"] == "segmentation" and body["coverage"]["tree"] == 75.0


def test_analysis_falls_back_to_boxes_without_double_counting(client, monkeypatch):
    monkeypatch.setattr(registry, "segmenter", None)
    body = client.post("/api/analysis", files=png()).json()
    # two overlapping 50x50 boxes cover 4375 px, not 5000
    assert body["source"] == "detection"
    assert body["coverage"] == {"building": 43.75, "road": 10.0}


def test_environmental_impact(client):
    body = client.post("/api/environmental-impact", files=png()).json()
    assert body["level"] == "healthy" and body["green_score"] == 75.0


def test_rejects_non_image(client):
    r = client.post("/api/detect", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_no_detector_gives_503(client, monkeypatch):
    monkeypatch.setattr(registry, "detector", None)
    assert client.post("/api/detect", files=png()).status_code == 503


@pytest.mark.parametrize("cov,level", [
    ({}, "unknown"),
    ({"tree": 70}, "healthy"),
    ({"tree": 40, "building": 20}, "balanced"),
    ({"building": 80, "tree": 5}, "critical"),
    ({"building": 55, "tree": 10}, "danger"),
    ({"building": 30, "tree": 20}, "warning"),
])
def test_impact_levels(cov, level):
    assert calculate_impact(cov)["level"] == level
