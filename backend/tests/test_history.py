"""Results database: saving, cache hits, history listing and deletion."""
import numpy as np
import pytest

from app.services import satellite as sat
from tests.test_api import client  # noqa: F401  (fixture with stand-in models)

BBOX = [77.2111, 28.6279, 77.2223, 28.6351]


@pytest.fixture
def downloads(monkeypatch):
    """Stand-in for the Esri download; counts how often imagery is fetched."""
    calls = []

    async def fake_fetch(client, bbox, zoom, release):
        calls.append(release)
        rgb = np.full((128, 160, 3), 90, dtype=np.uint8)
        return {"rgb": rgb, "zoom": zoom, "meters_per_pixel": 0.5, "release": release,
                "area_ha": 0.5, "missing_tiles": 0}

    async def fake_releases(client):
        return [{"release": 1, "date": "2014-12-03", "title": "Wayback 2014"}]

    monkeypatch.setattr(sat, "fetch_image", fake_fetch)
    monkeypatch.setattr(sat, "list_releases", fake_releases)
    return calls


def test_analysis_is_saved_then_served_from_database(client, downloads):  # noqa: F811
    first = client.post("/api/satellite/analyze", json={"bbox": BBOX}).json()
    assert first["cached"] is False and first["saved_id"]

    second = client.post("/api/satellite/analyze", json={"bbox": BBOX}).json()
    assert second["cached"] is True and second["saved_id"] == first["saved_id"]
    assert second["impact"] == first["impact"]
    assert len(downloads) == 1                                   # no second download or model run

    third = client.post("/api/satellite/analyze", json={"bbox": BBOX, "refresh": True}).json()
    assert third["cached"] is False and third["saved_id"] != first["saved_id"]
    assert len(downloads) == 2


def test_different_date_is_not_a_cache_hit(client, downloads):  # noqa: F811
    client.post("/api/satellite/analyze", json={"bbox": BBOX, "release": 1})
    other = client.post("/api/satellite/analyze", json={"bbox": [77.0, 28.0, 77.01, 28.01]}).json()
    assert other["cached"] is False


def test_comparison_saved_and_listed(client, downloads):  # noqa: F811
    body = {"bbox": BBOX, "release_before": 1}
    first = client.post("/api/satellite/compare", json=body).json()
    assert first["cached"] is False
    assert client.post("/api/satellite/compare", json=body).json()["cached"] is True

    page = client.get("/api/history", params={"kind": "comparison"}).json()
    item = next(i for i in page["items"] if i["id"] == first["saved_id"])
    assert item["date"] == "2014-12-03" and item["date_after"] == "latest"
    assert item["changed_percent"] == first["changed_percent"]


def test_open_and_delete_history_entry(client, downloads):  # noqa: F811
    saved = client.post("/api/satellite/analyze", json={"bbox": BBOX, "refresh": True}).json()
    entry = client.get(f"/api/history/{saved['saved_id']}").json()
    assert entry["item"]["kind"] == "analysis"
    assert entry["result"]["scene"]["image"].startswith("data:image/png;base64,")

    assert client.delete(f"/api/history/{saved['saved_id']}").status_code == 204
    assert client.get(f"/api/history/{saved['saved_id']}").status_code == 404
    assert client.get("/api/health").json()["saved_results"] >= 1
