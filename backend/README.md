# UrbanEye backend (FastAPI)

Python API for the UrbanEye project. It replaces the direct Roboflow / Gradio calls of the original
Flutter app ([Sharakush/Urbaneye](https://github.com/Sharakush/Urbaneye)) so the React frontend only
talks to this server, and API keys never ship to the browser.

| Endpoint | What it does | Replaces in the original app |
|---|---|---|
| `GET  /api/health` | Shows which models are loaded | – |
| `GET  /api/classes` | Segmentation classes and their colours | – |
| `POST /api/detect?confidence=0.25` | Object detection: boxes, counts per class, annotated image | Gradio "Object Detection Dashboard" |
| `POST /api/segment` | U-Net++ land-cover map (8 classes), coverage %, mask and overlay images | new |
| `POST /api/analysis` | Coverage % per class | `analysis_page.dart` |
| `POST /api/environmental-impact` | Coverage, green/urban score, status, recommendations | `environmental_impact_page.dart` |
| `GET  /api/satellite/dates?lat=&lon=` | Dates with distinct imagery at that point (2014 → today) | new |
| `POST /api/satellite/analyze` | Downloads the satellite image of a map area, then segmentation + impact (+ detection) | new |
| `POST /api/satellite/compare` | Land-cover change of an area between two dates: change map, transitions, hectares | new |
| `GET  /api/history` | Saved analyses and comparisons, newest first (`?kind=analysis\|comparison`) | new |
| `GET  /api/history/{id}` | One saved result with its images | new |
| `DELETE /api/history/{id}` | Delete a saved result | new |
| `GET  /api/history/{id}/report.pdf` | PDF report of a saved analysis or comparison | new |

### Faster inference: ONNX Runtime and Fast / Accurate mode

Export the trained model to ONNX once (and again whenever you replace the `.pth` file):

```powershell
python scripts/export_onnx.py      # writes models/unetpp_oem8.onnx and checks it matches PyTorch
```

On CPU the backend then uses ONNX Runtime automatically (`SEG_ENGINE=auto`; set `torch` to force PyTorch).
Every analysis endpoint also takes `quality`: `"accurate"` (default) averages the image and its mirror
image, `"fast"` runs the model once. Measured on a laptop CPU (12 threads) with the trained model:

| Area | PyTorch, Accurate | ONNX, Accurate | ONNX, Fast |
|---|---|---|---|
| ~0.5 km (932 x 850 px) | 9.0 s | 4.1 s | 2.0 s |
| ~1 km (1864 x 1660 px) | 61.4 s | 27.3 s | 13.6 s |

ONNX gives exactly the same labels as PyTorch; Fast mode agrees with Accurate on about 94% of pixels.
Downloading the imagery adds a few seconds on top.

### PDF reports

`GET /api/history/{id}/report.pdf` builds a report from a saved result: location, imagery date, model
and mode, satellite image and land-cover map, coverage table with hectares, environmental assessment and
recommendations. Comparison reports add both dates, the change map, transitions and coverage change.

### Results database

Every `/analyze` and `/compare` result is saved in a database (`app/db.py`, SQLAlchemy):

- **History:** list, reopen and delete past results (`/api/history`, and the History page of the web app).
- **Cache:** the same area, date(s) and model return the saved result instantly (responses have
  `"cached": true` and a `saved_id`). Send `"refresh": true` to run the model again. Results for
  "latest imagery" are reused for `CACHE_LATEST_DAYS` days (default 7), because Esri updates it.
- **Storage:** SQLite file `backend/data/urbaneye.db` by default, created automatically. For a deployed
  server set `DATABASE_URL` to PostgreSQL in `.env`; no code changes are needed.

### Satellite imagery

Images come from **Esri World Imagery** (latest) and **Esri Wayback** (about 200 dated versions since 2014),
at ~0.5 m per pixel (zoom 18). That matches the 0.25–0.5 m OpenEarthMap training data. Sentinel-2 (10 m),
used by the reference change-detection project, is too coarse for this model. No API key is needed.
Show the attribution returned in `scene.attribution` wherever the image is displayed.

`/analyze` and `/compare` take a JSON body like:

```json
{"bbox": [77.2111, 28.6279, 77.2223, 28.6351], "release": 22869}
```

`bbox` is `[west, south, east, north]`. `release` comes from `/dates`; leave it out for the latest imagery.
Areas up to about 1 km across use zoom 18. Larger areas, up to about 4 km, fall back to coarser zooms automatically.

All `POST` endpoints take a multipart form with one field, `file` (JPG/PNG/TIF image).
Images come back as PNG data URLs, so they can go straight into `<img src=...>`.
Interactive docs: **http://localhost:8000/docs**

## Models

Place the weights in `backend/models/`:

| File | Where it comes from | Used by |
|---|---|---|
| `unetpp_oem8_best.pth` | Colab notebook `UrbanEye_UNetPP_HighAccuracy.ipynb` → `MyDrive/UrbanEye/checkpoints/unetpp_b4_oem8_v2/best.pth` (rename it) | `/segment`, `/analysis`, `/environmental-impact` |
| `yolo11_best.pt` | Your YOLO11 training run → `runs/.../weights/best.pt` (rename it) | `/detect` |

Without YOLO weights, set `ROBOFLOW_API_KEY` in `.env` to use the hosted Roboflow model instead.
Without the U-Net++ weights, `/analysis` and `/environmental-impact` fall back to box areas from the detector.

## Run it (Windows, PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # then edit .env if needed
uvicorn app.main:app --reload --port 8000
```

For an NVIDIA GPU, install the CUDA build of PyTorch first (see pytorch.org), then `pip install -r requirements.txt`.

Tests (no models needed): `pytest -q`

## Calling it from the React (Vite) frontend

```js
const API = "http://localhost:8000/api";

async function analyzeImage(file, endpoint = "environmental-impact") {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/${endpoint}`, { method: "POST", body: form });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
  return res.json();
}

// <input type="file" accept="image/*" onChange={async e => {
//   const r = await analyzeImage(e.target.files[0], "detect");
//   setAnnotated(r.annotated_image);      // <img src={annotated} />
//   setCounts(r.counts);                  // { building: 12, road: 4, ... }
// }} />
```

Example `/api/environmental-impact` response:

```json
{
  "source": "segmentation",
  "coverage": {"bareland": 1.2, "rangeland": 10.4, "developed space": 14.0, "road": 8.1,
               "tree": 30.5, "water": 2.3, "agriculture land": 9.6, "building": 23.9},
  "status": "Moderate — Unbalanced Land Use ⚠️",
  "level": "warning",
  "green_score": 41.1,
  "urban_score": 39.4,
  "recommendations": ["Land use is unbalanced — ...", "..."]
}
```

## Differences from the original Flutter logic

- **Coverage** comes from the U-Net++ pixel map when available, which measures area properly. In box mode, overlapping boxes are counted once, so coverage can no longer exceed 100%.
- **Impact score** uses the same formula and thresholds. The 8-class model adds rangeland and agriculture to the green score (×0.5) and developed space to the urban score (×0.7).
- **"Critical" level** is now checked before "danger". In the Dart code it could never appear for low green cover.

## Project layout

```
backend/
  app/
    main.py          FastAPI app, CORS, startup model loading
    routes.py        upload endpoints + shared result builders
    satellite_routes.py  satellite dates / analyze / compare endpoints (saved + cached)
    history_routes.py    saved results: list / open / delete
    db.py            results database (SQLite or PostgreSQL via SQLAlchemy)
    config.py        settings from .env
    models.py        loads U-Net++ / YOLO / Roboflow once at startup
    schemas.py       response models
    services/
      segmenter.py   U-Net++ inference, PyTorch or ONNX Runtime (tiled, Fast/Accurate) + coverage
      report.py      PDF reports (ReportLab)
      detector.py    YOLO11 and Roboflow detectors, counts, annotation, box coverage
      impact.py      environmental impact score and recommendations
      satellite.py   Esri tile download/stitching, Wayback date discovery
      change.py      before/after label comparison, transitions, change map
      images.py      upload decoding, PNG data URLs
  scripts/export_onnx.py  export the .pth model to ONNX
  models/            put .pth / .pt / .onnx weights here (git-ignored)
  tests/test_api.py
```
