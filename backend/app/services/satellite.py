"""Satellite imagery for a bounding box, from Esri World Imagery (current) and Esri Wayback
(dated archive since 2014). Sub-metre resolution, which matches the 0.25-0.5 m OpenEarthMap
training data. No API key needed; attribution must be shown with the image."""
import asyncio
import io
import math
import re
import time

import httpx
import numpy as np
from PIL import Image

CURRENT_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
WAYBACK_URL = ("https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/"
               "default028mm/MapServer/tile/{release}/{z}/{y}/{x}")
WAYBACK_CONFIG = "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json"
ATTRIBUTION = "Imagery © Esri, Maxar, Earthstar Geographics, and the GIS User Community"
TILE = 256
HEADERS = {"User-Agent": "UrbanEye/1.0 (academic project)"}
_RELEASE_IN_URL = re.compile(r"/tile/(\d+)/", re.I)


class SatelliteError(ValueError):
    pass


# ---------------------------------------------------------------- geometry (Web Mercator)

def lonlat_to_pixel(lon: float, lat: float, z: int) -> tuple[float, float]:
    n = TILE * 2 ** z
    lat = max(-85.0511, min(85.0511, lat))
    r = math.radians(lat)
    return (lon + 180) / 360 * n, (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n


def meters_per_pixel(lat: float, z: int) -> float:
    return 156543.03392 * math.cos(math.radians(lat)) / 2 ** z


def validate_bbox(bbox: list[float]) -> tuple[float, float, float, float]:
    if len(bbox) != 4:
        raise SatelliteError("bbox must be [west, south, east, north]")
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -85 <= south < north <= 85):
        raise SatelliteError("bbox must be [west, south, east, north] in degrees, west < east, south < north")
    return west, south, east, north


def pixel_size(bbox, z: int) -> tuple[int, int]:
    west, south, east, north = bbox
    x0, y0 = lonlat_to_pixel(west, north, z)
    x1, y1 = lonlat_to_pixel(east, south, z)
    return round(x1 - x0), round(y1 - y0)


def choose_zoom(bbox, max_pixels: int, preferred: int, min_zoom: int = 16) -> int:
    """Highest zoom (finest detail) not above `preferred` whose image fits in max_pixels."""
    for z in range(preferred, min_zoom - 1, -1):
        w, h = pixel_size(bbox, z)
        if w * h <= max_pixels:
            return z
    w, h = pixel_size(bbox, min_zoom)
    mpp = meters_per_pixel((bbox[1] + bbox[3]) / 2, min_zoom)
    raise SatelliteError(f"Area too large ({w * mpp / 1000:.1f} × {h * mpp / 1000:.1f} km). "
                         f"Select a smaller area.")


# ---------------------------------------------------------------- Wayback releases (dates)

_releases: list[dict] = []
_releases_time = 0.0
_dates_cache: dict[tuple[int, int, int], list[dict]] = {}


async def list_releases(client: httpx.AsyncClient) -> list[dict]:
    """All archive versions, newest first: [{release, date, title}]. Cached for 12 h."""
    global _releases, _releases_time
    if _releases and time.time() - _releases_time < 12 * 3600:
        return _releases
    resp = await client.get(WAYBACK_CONFIG)
    resp.raise_for_status()
    out = []
    for key, item in resp.json().items():
        m = re.search(r"(\d{4}-\d{2}-\d{2})", item.get("itemTitle", ""))
        if m:
            out.append({"release": int(key), "date": m.group(1), "title": item["itemTitle"]})
    _releases = sorted(out, key=lambda r: r["date"], reverse=True)
    _releases_time = time.time()
    return _releases


async def available_dates(client: httpx.AsyncClient, lat: float, lon: float, zoom: int = 17) -> list[dict]:
    """Distinct imagery versions that exist at this point, newest first.

    Wayback redirects a request for release R to the older release whose imagery R still shows,
    so following the redirect for every release reveals when the imagery actually changed."""
    px, py = lonlat_to_pixel(lon, lat, zoom)
    key = (zoom, int(px // TILE), int(py // TILE))
    if key in _dates_cache:
        return _dates_cache[key]
    releases = await list_releases(client)
    by_id = {r["release"]: r for r in releases}
    sem = asyncio.Semaphore(24)

    async def effective(rel: int) -> int | None:
        url = WAYBACK_URL.format(release=rel, z=key[0], x=key[1], y=key[2])
        async with sem:
            try:
                r = await client.get(url, follow_redirects=False)
            except httpx.HTTPError:
                return None
        if r.status_code == 200:
            return rel
        if r.status_code in (301, 302, 303, 307, 308):
            m = _RELEASE_IN_URL.search(r.headers.get("location", ""))
            return int(m.group(1)) if m else None
        return None

    found = await asyncio.gather(*(effective(r["release"]) for r in releases))
    unique = {rel for rel in found if rel is not None and rel in by_id}
    dates = sorted((by_id[rel] for rel in unique), key=lambda r: r["date"], reverse=True)
    _dates_cache[key] = dates
    return dates


# ---------------------------------------------------------------- image download

async def fetch_image(client: httpx.AsyncClient, bbox: list[float], zoom: int,
                      release: int | None = None) -> dict:
    """Stitch tiles into an RGB array covering exactly the bbox at the given zoom."""
    west, south, east, north = validate_bbox(bbox)
    x0, y0 = lonlat_to_pixel(west, north, zoom)
    x1, y1 = lonlat_to_pixel(east, south, zoom)
    tx0, ty0, tx1, ty1 = int(x0 // TILE), int(y0 // TILE), int(x1 // TILE), int(y1 // TILE)
    cols, rows = tx1 - tx0 + 1, ty1 - ty0 + 1
    canvas = np.full((rows * TILE, cols * TILE, 3), 128, dtype=np.uint8)
    sem = asyncio.Semaphore(16)
    effective_releases: list[int] = []

    async def get_tile(tx: int, ty: int) -> bool:
        url = (WAYBACK_URL.format(release=release, z=zoom, x=tx, y=ty) if release
               else CURRENT_URL.format(z=zoom, x=tx, y=ty))
        async with sem:
            for attempt in range(3):
                try:
                    r = await client.get(url, follow_redirects=True)
                    break
                except httpx.HTTPError:
                    if attempt == 2:
                        return False
                    await asyncio.sleep(0.5 * (attempt + 1))
        if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
            return False
        if release:
            m = _RELEASE_IN_URL.search(str(r.url))
            if m:
                effective_releases.append(int(m.group(1)))
        tile = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))
        oy, ox = (ty - ty0) * TILE, (tx - tx0) * TILE
        canvas[oy:oy + TILE, ox:ox + TILE] = tile[:TILE, :TILE]
        return True

    ok = await asyncio.gather(*(get_tile(tx, ty) for ty in range(ty0, ty1 + 1)
                                for tx in range(tx0, tx1 + 1)))
    missing = ok.count(False)
    if missing > 0.25 * len(ok):
        raise SatelliteError("No imagery at this resolution for the selected date here. "
                             "Choose another date from the list of available dates.")

    ox, oy = int(x0 - tx0 * TILE), int(y0 - ty0 * TILE)
    w, h = max(1, round(x1 - x0)), max(1, round(y1 - y0))
    rgb = np.ascontiguousarray(canvas[oy:oy + h, ox:ox + w])
    lat_c = (south + north) / 2
    mpp = meters_per_pixel(lat_c, zoom)
    # The release that actually supplied most tiles (Wayback reuses older imagery).
    eff = max(set(effective_releases), key=effective_releases.count) if effective_releases else release
    return {"rgb": rgb, "zoom": zoom, "meters_per_pixel": mpp, "release": eff,
            "area_ha": w * h * mpp * mpp / 10_000, "missing_tiles": missing}


def new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=HEADERS, timeout=httpx.Timeout(20.0),
                             limits=httpx.Limits(max_connections=32))
