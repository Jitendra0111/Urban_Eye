import { useEffect, useState } from "react";
import { MapContainer, Rectangle, TileLayer, useMapEvents } from "react-leaflet";
import { ATTRIBUTION, LABEL_TILES, LATEST_TILES, waybackTiles } from "../geo";

const START = { center: [28.6315, 77.2167], zoom: 16 }; // Connaught Place, New Delhi

/** Two clicks (or taps) set opposite corners; the rectangle follows the pointer in between. */
function DrawCorners({ drawing, onDone }) {
  const [start, setStart] = useState(null);
  const [cursor, setCursor] = useState(null);
  const map = useMapEvents({
    click(e) {
      if (!drawing) return;
      if (!start) {
        setStart(e.latlng);
        return;
      }
      const a = start;
      const b = e.latlng;
      setStart(null);
      setCursor(null);
      onDone([
        Math.min(a.lng, b.lng),
        Math.min(a.lat, b.lat),
        Math.max(a.lng, b.lng),
        Math.max(a.lat, b.lat),
      ]);
    },
    mousemove(e) {
      if (drawing && start) setCursor(e.latlng);
    },
  });

  useEffect(() => {
    map.getContainer().style.cursor = drawing ? "crosshair" : "";
    if (!drawing) setStart(null);
  }, [drawing, map]);

  if (!start || !cursor) return null;
  return <Rectangle bounds={[start, cursor]} pathOptions={{ className: "area-draft" }} />;
}

function SearchBox({ map }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [message, setMessage] = useState("");

  async function search(e) {
    e.preventDefault();
    if (!query.trim()) return;
    setMessage("Searching…");
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(query)}`,
      );
      const data = await res.json();
      setResults(data);
      setMessage(data.length ? "" : "No places found. Try a city or landmark name.");
    } catch {
      setMessage("Place search is unavailable. Pan the map instead.");
    }
  }

  function go(place) {
    map?.flyTo([Number(place.lat), Number(place.lon)], 17);
    setResults([]);
    setQuery(place.display_name.split(",")[0]);
  }

  return (
    <div className="map-search">
      <form onSubmit={search} role="search">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search a place, e.g. Bandra, Mumbai"
          aria-label="Search a place"
        />
        <button type="submit" className="btn btn-small">Find</button>
      </form>
      {message && <p className="map-search-msg">{message}</p>}
      {results.length > 0 && (
        <ul className="map-search-results">
          {results.map((r) => (
            <li key={r.place_id}>
              <button type="button" onClick={() => go(r)}>{r.display_name}</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Satellite map for choosing an analysis area.
 * bbox: [west, south, east, north] | null. release: Wayback release shown as the basemap (null = latest).
 */
export default function AreaPicker({ bbox, onChange, release = null }) {
  const [map, setMap] = useState(null);
  const [drawing, setDrawing] = useState(false);

  function useView() {
    const b = map.getBounds();
    // Slightly inset so the rectangle stays visible inside the map frame.
    const padX = (b.getEast() - b.getWest()) * 0.08;
    const padY = (b.getNorth() - b.getSouth()) * 0.08;
    onChange([b.getWest() + padX, b.getSouth() + padY, b.getEast() - padX, b.getNorth() - padY]);
    setDrawing(false);
  }

  return (
    <div className="area-picker">
      <MapContainer
        center={START.center}
        zoom={START.zoom}
        maxZoom={19}
        ref={setMap}
        className="map"
        doubleClickZoom={!drawing}
      >
        <TileLayer
          key={release ?? "latest"}
          url={release ? waybackTiles(release) : LATEST_TILES}
          attribution={ATTRIBUTION}
          maxZoom={19}
          maxNativeZoom={19}
        />
        <TileLayer url={LABEL_TILES} maxZoom={19} opacity={0.75} />
        <DrawCorners
          drawing={drawing}
          onDone={(b) => {
            onChange(b);
            setDrawing(false);
          }}
        />
        {bbox && (
          <Rectangle
            bounds={[[bbox[1], bbox[0]], [bbox[3], bbox[2]]]}
            pathOptions={{ className: "area-selected" }}
          />
        )}
      </MapContainer>

      <SearchBox map={map} />

      <div className="map-tools" role="toolbar" aria-label="Area tools">
        <button
          type="button"
          className={`btn btn-small ${drawing ? "btn-active" : ""}`}
          onClick={() => setDrawing((d) => !d)}
          aria-pressed={drawing}
        >
          {drawing ? "Cancel drawing" : "Draw area"}
        </button>
        <button type="button" className="btn btn-small" onClick={useView} disabled={!map}>
          Use this view
        </button>
        {bbox && (
          <button type="button" className="btn btn-small btn-quiet" onClick={() => onChange(null)}>
            Clear
          </button>
        )}
      </div>
      {drawing && <p className="map-hint">Click one corner of the area, then the opposite corner.</p>}
    </div>
  );
}
