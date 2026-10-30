# UrbanEye frontend (React + Vite)

| Page | What it does | Backend endpoint |
|---|---|---|
| **Home** `/` | Overview and model status | `GET /api/health` |
| **Map analysis** `/map` | Search a place, draw an area on the satellite map, choose an imagery date, get the land-cover map, coverage and hectares per class, and the environmental assessment | `/api/satellite/dates`, `/api/satellite/analyze` |
| **Change over time** `/change` | Same area at two dates: before/after slider, change map, biggest transitions (e.g. tree → building, in ha), coverage change, impact at each date | `/api/satellite/compare` |
| **Timeline** `/timeline` | Analyse one area at 4–12 imagery dates since 2014: one small chart per class, environmental scores over time, table of every date | `/api/satellite/dates`, `/api/satellite/analyze` (once per date) |
| **History** `/history` | Saved analyses and comparisons: reopen, download PDF, delete | `/api/history` |
| **Photo analysis** `/photo` | Upload your own aerial photo: land cover, detected objects, impact | `/api/segment`, `/api/detect`, `/api/environmental-impact` |

## Run

Start the backend first (see `../backend/README.md`), then:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. During development, Vite forwards `/api/...` to the backend at
`http://127.0.0.1:8000`, so nothing else needs configuring. To use another backend address:
`$env:VITE_BACKEND_URL="http://192.168.1.10:8000"; npm run dev`.

Production build: `npm run build` creates `dist/`. If it is served from a different address than the
backend, set `VITE_API_URL` (see `.env.example`) before building, and add that address to
`CORS_ORIGINS` in the backend `.env`.

Every analysis page has a **Fast / Accurate** switch (remembered in the browser), and saved results
have a **Download PDF report** button.

## Using the map

1. Search a place, or pan and zoom the map.
2. Press **Draw area** and click two opposite corners, or press **Use this view**.
3. Choose an imagery date. The map switches to that date's imagery so you can check it first.
4. Press **Analyse area** or **Compare dates**.

Areas of 0.5–1 km across give the best results: the image is fetched at ~0.5 m per pixel, the same
detail the U-Net++ model was trained on.

## Code layout

```
src/
  api.js                 all backend calls
  classes.js             the 8 classes and their colours
  geo.js                 map maths (area size, resolution), tile URLs
  hooks.js               backend status, available dates for an area
  App.jsx                navigation and pages
  pages/                 Home, MapAnalysis, ChangeOverTime, PhotoAnalysis
  components/            AreaPicker (map), CompositionStrip, CoverageTable,
                         ImpactPanel, ImageViewer, BeforeAfter, DateSelect, ...
  styles.css
```

Place search uses OpenStreetMap Nominatim. Imagery is © Esri, Maxar, Earthstar Geographics, and the
credit is shown under every image.
