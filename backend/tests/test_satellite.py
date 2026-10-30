"""Offline tests for satellite geometry and change detection, plus API validation:  pytest -q"""
import numpy as np
import pytest

from app.services import satellite as sat
from app.services.change import compare
from tests.test_api import client  # noqa: F401  (fixture with stand-in models)


def test_pixel_size_and_zoom_choice():
    bbox = [77.2090, 28.6300, 77.2190, 28.6380]          # ~1 km x 0.9 km in Delhi
    w18, h18 = sat.pixel_size(bbox, 18)
    assert 1800 < w18 < 1900 and 1600 < h18 < 1800
    assert sat.choose_zoom(bbox, 2048 * 2048, preferred=18) == 18
    assert sat.choose_zoom(bbox, 1024 * 1024, preferred=18) == 17
    assert 0.5 < sat.meters_per_pixel(28.63, 18) < 0.55


def test_area_too_large():
    with pytest.raises(sat.SatelliteError, match="too large"):
        sat.choose_zoom([77.0, 28.5, 77.5, 29.0], 2048 * 2048, preferred=18)


@pytest.mark.parametrize("bbox", [[77.3, 28.6, 77.2, 28.7], [0, 0, 1], [-200, 0, 0, 1]])
def test_invalid_bbox(bbox):
    with pytest.raises(sat.SatelliteError):
        sat.validate_bbox(bbox)


def test_compare_label_maps():
    before = np.full((10, 10), 4, dtype=np.uint8)         # all tree
    after = before.copy()
    after[:3] = 7                                          # 30% became building
    rgb = np.full((10, 10, 3), 200, dtype=np.uint8)
    out = compare(before, after, rgb, area_ha=2.0)
    assert out["changed_percent"] == 30.0 and out["changed_hectares"] == 0.6
    assert out["transitions"][0] == {"from_class": "tree", "to_class": "building",
                                     "percent": 30.0, "hectares": 0.6}
    assert tuple(out["change_map"][0, 0]) == (222, 31, 7)  # building colour on changed pixels


def test_analyze_rejects_bad_bbox(client):  # noqa: F811
    r = client.post("/api/satellite/analyze", json={"bbox": [10, 10, 5, 5]})
    assert r.status_code == 422
