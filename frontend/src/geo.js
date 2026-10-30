// Web Mercator helpers that mirror backend/app/services/satellite.py, so the UI can tell the user
// the resolution and whether an area fits before sending the request.
export const MAX_PIXELS = 2048 * 2048;
export const PREFERRED_ZOOM = 18;
const MIN_ZOOM = 16;

export const LATEST_TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
export const waybackTiles = (release) =>
  `https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/${release}/{z}/{y}/{x}`;
export const LABEL_TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}";
export const ATTRIBUTION = "Imagery © Esri, Maxar, Earthstar Geographics";

function toPixel(lon, lat, z) {
  const n = 256 * 2 ** z;
  const r = (Math.max(-85.0511, Math.min(85.0511, lat)) * Math.PI) / 180;
  return [((lon + 180) / 360) * n, ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * n];
}

export const metersPerPixel = (lat, z) => (156543.03392 * Math.cos((lat * Math.PI) / 180)) / 2 ** z;

/** Size of a bbox [west, south, east, north] in metres, and the zoom the backend will use. */
export function describeBbox(bbox) {
  const [w, s, e, n] = bbox;
  const lat = (s + n) / 2;
  const sizeAt = (z) => {
    const [x0, y0] = toPixel(w, n, z);
    const [x1, y1] = toPixel(e, s, z);
    return [x1 - x0, y1 - y0];
  };
  const [pw, ph] = sizeAt(PREFERRED_ZOOM);
  const mpp = metersPerPixel(lat, PREFERRED_ZOOM);
  const widthM = pw * mpp;
  const heightM = ph * mpp;
  let zoom = null;
  for (let z = PREFERRED_ZOOM; z >= MIN_ZOOM; z--) {
    const [a, b] = sizeAt(z);
    if (a * b <= MAX_PIXELS) {
      zoom = z;
      break;
    }
  }
  return {
    widthM,
    heightM,
    areaHa: (widthM * heightM) / 10000,
    zoom,
    resolution: zoom ? metersPerPixel(lat, zoom) : null,
    tooSmall: pw < 64 || ph < 64,
    center: [(s + n) / 2, (w + e) / 2],
  };
}

export const formatMeters = (m) => (m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${Math.round(m)} m`);
export const formatHa = (ha) => (ha >= 100 ? `${(ha / 100).toFixed(2)} km²` : `${ha.toFixed(ha < 10 ? 2 : 1)} ha`);
export const formatCoord = (v, pos, neg) => `${Math.abs(v).toFixed(4)}°${v >= 0 ? pos : neg}`;
