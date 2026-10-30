import { useState } from "react";
import { api } from "../api";
import AreaPicker from "../components/AreaPicker";
import AreaSummary, { bboxReady } from "../components/AreaSummary";
import CompositionStrip, { Legend } from "../components/CompositionStrip";
import CoverageTable from "../components/CoverageTable";
import DateSelect from "../components/DateSelect";
import { Empty, ErrorNote, Working } from "../components/Feedback";
import ImageViewer from "../components/ImageViewer";
import ImpactPanel from "../components/ImpactPanel";
import { PageHead, Stats, Step, useRevealOn } from "../components/Layout";
import { classInfo } from "../classes";
import { useAreaDates, useHealth } from "../hooks";

const dateLabel = (d) =>
  d === "latest" ? "latest imagery" : new Date(d).toLocaleDateString("en-IN", { dateStyle: "medium" });

const topClass = (coverage) => {
  const [key, pct] = Object.entries(coverage).sort((a, b) => b[1] - a[1])[0] ?? [];
  return key ? `${classInfo(key).label} ${pct.toFixed(0)}%` : "–";
};

export default function MapAnalysis() {
  const { health } = useHealth();
  const [bbox, setBbox] = useState(null);
  const [release, setRelease] = useState("");
  const [detect, setDetect] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const dates = useAreaDates(bbox);
  const resultsRef = useRevealOn(result);

  async function analyze() {
    setBusy(true);
    setError(null);
    try {
      setResult(
        await api.analyzeArea({ bbox, release: release ? Number(release) : null, detect }),
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const seg = result?.segmentation;
  const scene = result?.scene;
  const ready = bboxReady(bbox);

  return (
    <div className="page">
      <PageHead title="Map analysis">Choose an area on the satellite map and find out what its land is made of.</PageHead>

      <div className="workbench">
        <aside className="panel" aria-label="Analysis settings">
          <Step n={1} title="Choose an area" done={ready}>
            <AreaSummary bbox={bbox} />
          </Step>

          <Step n={2} title="Pick the imagery date" done={ready && !dates.loading}>
            <DateSelect
              id="date"
              label="Imagery date"
              dates={dates.dates}
              value={release}
              onChange={setRelease}
              loading={dates.loading}
            />
            {dates.error && <p className="note note-warn">{dates.error}</p>}
            {bbox && !dates.loading && dates.dates.length > 0 && (
              <p className="hint">{dates.dates.length} dates with imagery here. The map shows the selected date.</p>
            )}
            {health?.detector && (
              <label className="check">
                <input type="checkbox" checked={detect} onChange={(e) => setDetect(e.target.checked)} />
                Also detect objects ({health.detector})
              </label>
            )}
          </Step>

          <Step n={3} title="Run the analysis" done={Boolean(result)}>
            <button type="button" className="btn btn-primary btn-block" onClick={analyze} disabled={!ready || busy}>
              {busy ? "Analysing…" : "Analyse area"}
            </button>
            {busy && <Working>Downloading imagery and running the model. This takes 5–60 seconds.</Working>}
            <ErrorNote error={error} />
          </Step>
        </aside>

        <AreaPicker bbox={bbox} onChange={setBbox} release={release ? Number(release) : null} />
      </div>

      {!result && !busy && (
        <Empty title="Results appear here">
          Select an area, pick a date, and press Analyse area. Areas around 500 m to 1 km across give the most detailed results.
        </Empty>
      )}

      {result && (
        <section className="results" aria-label="Results" ref={resultsRef}>
          <div className="results-head">
            <h2>Land cover · {dateLabel(scene.date)}</h2>
            <p className="mono muted">
              {scene.width} × {scene.height} px · {scene.meters_per_pixel} m/px · {scene.area_ha} ha
            </p>
          </div>

          <Stats
            items={[
              { label: "Area", value: scene.area_ha, unit: "ha" },
              { label: "Largest class", value: topClass(result.impact.coverage) },
              { label: "Green score", value: result.impact.green_score.toFixed(1), tone: "green" },
              { label: "Urban score", value: result.impact.urban_score.toFixed(1), tone: "urban" },
            ]}
          />

          <div className="card">
            <CompositionStrip coverage={result.impact.coverage} size="lg" />
          </div>

          <div className="results-grid">
            <div className="card">
              <ImageViewer
                caption={scene.attribution}
                views={[
                  { key: "overlay", label: "Land cover overlay", src: seg?.overlay_image },
                  { key: "mask", label: "Land cover map", src: seg?.mask_image },
                  { key: "image", label: "Satellite image", src: scene.image },
                  { key: "detect", label: "Detected objects", src: result.detection?.annotated_image },
                ]}
              />
            </div>
            <div className="stack">
              <h3 className="section-title">Coverage by class</h3>
              <CoverageTable coverage={result.impact.coverage} areaHa={scene.area_ha} />
              {seg && <Legend />}
              {result.detection && (
                <p className="mono muted">
                  Objects:{" "}
                  {Object.entries(result.detection.counts)
                    .map(([k, v]) => `${k} ${v}`)
                    .join(" · ") || "none found"}
                </p>
              )}
            </div>
          </div>

          <ImpactPanel impact={result.impact} />
        </section>
      )}
    </div>
  );
}
