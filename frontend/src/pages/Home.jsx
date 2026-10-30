import { Link } from "react-router-dom";
import { CLASSES } from "../classes";
import { useHealth } from "../hooks";

const TASKS = [
  {
    to: "/map",
    title: "Map analysis",
    text: "Draw an area on the satellite map. Get its land-cover map, the share and hectares of each class, and an environmental assessment.",
    action: "Analyse an area",
  },
  {
    to: "/change",
    title: "Change over time",
    text: "Pick an area and two imagery dates between 2014 and today. See where trees became buildings, fields became roads, and by how much.",
    action: "Compare two dates",
  },
  {
    to: "/timeline",
    title: "Timeline",
    text: "Analyse one area at up to 12 imagery dates since 2014 and chart how every land-cover class grew or shrank.",
    action: "Build a timeline",
  },
  {
    to: "/photo",
    title: "Photo analysis",
    text: "Upload your own aerial or satellite photo to map its land cover, detect objects, and assess its environmental impact.",
    action: "Upload a photo",
  },
];

export default function Home() {
  const { health, error } = useHealth();
  return (
    <div className="page home">
      <section className="hero">
        <p className="eyebrow">Urban land-cover mapping from satellite imagery</p>
        <h1>What is this land made of?</h1>
        <p className="lede">
          UrbanEye labels every pixel of a satellite image as one of eight land-cover classes, measures
          how much of each the area holds, and tracks how it changed since 2014.
        </p>

        <div className="hero-strip" aria-label="The eight land-cover classes the model maps">
          {CLASSES.map((c, i) => (
            <div key={c.key} className="hero-seg" style={{ "--c": c.color, "--i": i }}>
              <span className="hero-seg-bar" />
              <span className="hero-seg-label">{c.label}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="tasks" aria-label="What you can do">
        {TASKS.map((t) => (
          <Link key={t.to} to={t.to} className="task">
            <h2>{t.title}</h2>
            <p>{t.text}</p>
            <span className="task-action">{t.action} →</span>
          </Link>
        ))}
      </section>

      <section className="system">
        <h2 className="section-title">System</h2>
        {error && (
          <p className="note note-error">
            {error}
          </p>
        )}
        {health && (
          <dl className="readout readout-wide">
            <div>
              <dt>Land-cover model</dt>
              <dd>{health.segmentation_model ? "U-Net++ · EfficientNet-B4 · 8 classes" : "Not loaded"}</dd>
            </div>
            <div>
              <dt>Object detector</dt>
              <dd>{health.detector ?? "Not configured"}</dd>
            </div>
            <div>
              <dt>Running on</dt>
              <dd>{health.device.toUpperCase()}</dd>
            </div>
            <div>
              <dt>Saved results</dt>
              <dd>{health.saved_results ?? "Database unavailable"}</dd>
            </div>
            <div>
              <dt>Imagery</dt>
              <dd>Esri World Imagery and Wayback archive, ~0.5 m per pixel</dd>
            </div>
          </dl>
        )}
        {health && !health.segmentation_model && (
          <p className="note note-warn">
            Copy your trained <code>best.pth</code> to <code>backend/models/unetpp_oem8_best.pth</code> and
            restart the backend to enable land-cover mapping.
          </p>
        )}
      </section>
    </div>
  );
}
