import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import CompositionStrip, { Legend } from "../components/CompositionStrip";
import CoverageTable from "../components/CoverageTable";
import { Empty, ErrorNote, Working } from "../components/Feedback";
import ImageViewer from "../components/ImageViewer";
import ImpactPanel from "../components/ImpactPanel";
import { PageHead, QualitySwitch, Stats, Step, useQuality, useRevealOn } from "../components/Layout";
import { classInfo } from "../classes";
import { useHealth } from "../hooks";

const topClass = (coverage) => {
  const [key, pct] = Object.entries(coverage).sort((a, b) => b[1] - a[1])[0] ?? [];
  return key ? `${classInfo(key).label} ${pct.toFixed(0)}%` : "–";
};

export default function PhotoAnalysis() {
  const { health } = useHealth();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [quality, setQuality] = useQuality();
  const input = useRef(null);
  const resultsRef = useRevealOn(result);

  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  function choose(f) {
    if (!f) return;
    if (!f.type.startsWith("image/") && !/\.tiff?$/i.test(f.name)) {
      setErrors(["Choose an image file (JPG, PNG or TIF)."]);
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setErrors([]);
  }

  async function analyze() {
    setBusy(true);
    setErrors([]);
    const jobs = {
      impact: api.impact(file, quality),
      segment: health?.segmentation_model ? api.segment(file, quality) : null,
      detect: health?.detector ? api.detect(file) : null,
    };
    const keys = Object.keys(jobs).filter((k) => jobs[k]);
    const settled = await Promise.allSettled(keys.map((k) => jobs[k]));
    const out = {};
    const errs = [];
    settled.forEach((s, i) => {
      if (s.status === "fulfilled") out[keys[i]] = s.value;
      else errs.push(s.reason.message);
    });
    setResult(Object.keys(out).length ? out : null);
    setErrors([...new Set(errs)]);
    setBusy(false);
  }

  const objectCount = result?.detect ? Object.values(result.detect.counts).reduce((s, v) => s + v, 0) : null;

  return (
    <div className="page">
      <PageHead title="Photo analysis">
        Upload an aerial or satellite photo taken from directly above. Results are best at 0.25–1 m per pixel.
      </PageHead>

      <div className="workbench">
        <aside className="panel" aria-label="Photo settings">
          <Step n={1} title="Choose a photo" done={Boolean(file)}>
            <button type="button" className="btn btn-block" onClick={() => input.current.click()}>
              {file ? "Choose another photo" : "Choose a photo"}
            </button>
            {file ? (
              <p className="mono muted">{file.name} · {(file.size / 1024 / 1024).toFixed(1)} MB</p>
            ) : (
              <p className="hint">Or drop an image on the area to the right. JPG, PNG or TIF.</p>
            )}
            <input
              ref={input}
              type="file"
              accept="image/*,.tif,.tiff"
              hidden
              onChange={(e) => choose(e.target.files[0])}
            />
          </Step>

          <Step n={2} title="Run the analysis" done={Boolean(result)}>
            <QualitySwitch value={quality} onChange={setQuality} disabled={busy} />
            <button type="button" className="btn btn-primary btn-block" onClick={analyze} disabled={!file || busy}>
              {busy ? "Analysing…" : "Analyse photo"}
            </button>
            {busy && <Working>Running the models on your photo.</Working>}
            {errors.map((e) => (
              <ErrorNote key={e} error={e} />
            ))}
          </Step>
        </aside>

        <div
          className={`dropzone ${dragging ? "dropzone-over" : ""} ${preview ? "dropzone-filled" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            choose(e.dataTransfer.files[0]);
          }}
        >
          {preview ? (
            <img src={preview} alt="Selected photo" className="dropzone-preview" />
          ) : (
            <>
              <svg viewBox="0 0 24 24" width="40" height="40" aria-hidden="true" className="dropzone-icon">
                <path d="M12 16V4m0 0-4 4m4-4 4 4M4 15v5h16v-5" fill="none" stroke="currentColor" strokeWidth="1.6"
                  strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="dropzone-text">Drop an image here</p>
              <button type="button" className="btn" onClick={() => input.current.click()}>
                Choose a photo
              </button>
            </>
          )}
        </div>
      </div>

      {!result && !busy && !errors.length && (
        <Empty title="No photo analysed yet">Choose a photo, then press Analyse photo.</Empty>
      )}

      {result && (
        <section className="results" aria-label="Results" ref={resultsRef}>
          {result.impact && (
            <Stats
              items={[
                { label: "Largest class", value: topClass(result.impact.coverage) },
                { label: "Green score", value: result.impact.green_score.toFixed(1), tone: "green" },
                { label: "Urban score", value: result.impact.urban_score.toFixed(1), tone: "urban" },
                ...(objectCount != null ? [{ label: "Objects detected", value: objectCount }] : []),
              ]}
            />
          )}
          {result.impact && (
            <div className="card">
              <CompositionStrip coverage={result.impact.coverage} size="lg" />
            </div>
          )}
          <div className="results-grid">
            <div className="card">
              <ImageViewer
                views={[
                  { key: "overlay", label: "Land cover overlay", src: result.segment?.overlay_image },
                  { key: "mask", label: "Land cover map", src: result.segment?.mask_image },
                  { key: "detect", label: "Detected objects", src: result.detect?.annotated_image },
                  { key: "photo", label: "Original", src: preview },
                ]}
              />
            </div>
            <div className="stack">
              {result.impact && (
                <>
                  <h3 className="section-title">Coverage by class</h3>
                  <CoverageTable coverage={result.impact.coverage} />
                </>
              )}
              {result.segment && <Legend />}
              {result.detect && (
                <div>
                  <h3 className="section-title">Detected objects</h3>
                  <ul className="counts">
                    {Object.entries(result.detect.counts).map(([k, v]) => (
                      <li key={k}>
                        <span>{k}</span>
                        <span className="mono">{v}</span>
                      </li>
                    ))}
                    {!Object.keys(result.detect.counts).length && <li className="muted">No objects found</li>}
                  </ul>
                </div>
              )}
            </div>
          </div>
          {result.impact && <ImpactPanel impact={result.impact} />}
        </section>
      )}
    </div>
  );
}
