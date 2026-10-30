import { NavLink, Route, Routes } from "react-router-dom";
import { HealthContext, useHealth, useHealthCheck } from "./hooks";
import Home from "./pages/Home";
import MapAnalysis from "./pages/MapAnalysis";
import ChangeOverTime from "./pages/ChangeOverTime";
import PhotoAnalysis from "./pages/PhotoAnalysis";
import History from "./pages/History";
import Timeline from "./pages/Timeline";

const icon = {
  home: "M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z",
  map: "M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2zm0 0v14m6-12v14",
  change: "M4 7h13l-3-3m6 13H7l3 3",
  photo: "M4 6h3l2-2h6l2 2h3v13H4zM12 16a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z",
  history: "M3 12a9 9 0 1 0 3-6.7L3 8m0-5v5h5m4-1v5l3 2",
  timeline: "M3 20h18M5 16l4-5 4 3 6-8",
};

const NAV = [
  { to: "/", label: "Overview", icon: icon.home, end: true },
  { to: "/map", label: "Map analysis", icon: icon.map },
  { to: "/change", label: "Change over time", icon: icon.change },
  { to: "/timeline", label: "Timeline", icon: icon.timeline },
  { to: "/photo", label: "Photo analysis", icon: icon.photo },
  { to: "/history", label: "History", icon: icon.history },
];

function Icon({ d }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" className="nav-icon">
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Status() {
  const { health, error } = useHealth();
  let tone = "idle";
  let title = "Connecting…";
  let detail = "Checking the backend";
  if (error) {
    tone = "bad";
    title = "Backend offline";
    detail = "Start the FastAPI server on port 8000";
  } else if (health && !health.segmentation_model) {
    tone = "warn";
    title = "Model not loaded";
    detail = "Put unetpp_oem8_best.pth in backend/models";
  } else if (health) {
    tone = "good";
    title = "Model ready";
    detail = `U-Net++ · ${health.device.toUpperCase()}`;
  }
  return (
    <div className={`status status-${tone}`} role="status" title={error ?? undefined}>
      <span className="status-dot" aria-hidden="true" />
      <span className="status-text">
        <strong>{title}</strong>
        <span>{detail}</span>
      </span>
    </div>
  );
}

export default function App() {
  const health = useHealthCheck();
  return (
    <HealthContext.Provider value={health}>
      <a href="#main" className="skip-link">Skip to content</a>
      <div className="shell">
        <aside className="sidebar">
          <NavLink to="/" className="brand" aria-label="UrbanEye home">
            <span className="brand-mark" aria-hidden="true" />
            <span className="brand-name">UrbanEye</span>
          </NavLink>
          <nav aria-label="Main" className="nav">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
                <Icon d={n.icon} />
                <span>{n.label}</span>
              </NavLink>
            ))}
          </nav>
          <Status />
        </aside>

        <div className="workspace">
          <main id="main">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/map" element={<MapAnalysis />} />
              <Route path="/change" element={<ChangeOverTime />} />
              <Route path="/timeline" element={<Timeline />} />
              <Route path="/photo" element={<PhotoAnalysis />} />
              <Route path="/history" element={<History />} />
              <Route path="*" element={<Home />} />
            </Routes>
          </main>
          <footer className="footer">
            UrbanEye · U-Net++ land-cover segmentation trained on OpenEarthMap · Satellite imagery © Esri,
            Maxar, Earthstar Geographics
          </footer>
        </div>
      </div>
    </HealthContext.Provider>
  );
}
