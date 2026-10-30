import { useEffect, useState } from "react";
import { api } from "../api";
import AreaPicker from "../components/AreaPicker";
import AreaSummary, { bboxReady } from "../components/AreaSummary";
import BeforeAfter from "../components/BeforeAfter";
import CompositionStrip from "../components/CompositionStrip";
import CoverageTable from "../components/CoverageTable";
import DateSelect from "../components/DateSelect";
import { Empty, ErrorNote, Working } from "../components/Feedback";
import ImageViewer from "../components/ImageViewer";
import ImpactPanel from "../components/ImpactPanel";
import { PageHead, Stats, Step, useRevealOn } from "../components/Layout";
import { classInfo } from "../classes";
import { formatHa } from "../geo";
import { useAreaDates, useHealth } from "../hooks";

const fmtDate = (d) =>
  d === "latest" ? "Latest" : new Date(d).toLocaleDateString("en-IN", { year: "numeric", month: "short" });

export default function ChangeOverTime() {
  const { health } = useHealth();
  const [bbox, setBbox] = useState(null);
  const [before, setBefore] = useState("");
  const [after, setAfter] = useState("");
  const [view, setView] = useState("image");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const dates = useAreaDates(bbox);
  const resultsRef = useRevealOn(result);

  // Default "before" to the oldest available date whenever the area's dates change.
  useEffect(() => {
    const oldest = dates.dates.at(-1);
    setBefore(oldest ? String(oldest.release) : "");
  }, [dates.dates]);

  async function compare() {
    setBusy(true);
    setError(null);
    try {
      setResult(
        await api.compare({
          bbox,
          release_before: Number(before),
          release_after: after ? Number(after) : null,
        }),
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const modelMissing = health && !health.segmentation_model;
  const ready = bboxReady(bbox);
  const canRun = ready && before && !busy && !modelMissing;
  const b = result?.before;
  const a = result?.after;
  const pick = (r) => (view === "image" ? r.scene.image : r.segmentation.mask_image);
  const top = result?.transitions[0];

  return (
    <div className="page">
      <PageHead title="Change over time">
        Compare the land cover of one area at two dates. Older imagery goes back to 2014 in most cities.
      </PageHead>

      <div className="workbench">
        <aside className="panel" aria-label="Comparison settings">
          <Step n={1} title="Choose an area" done={ready}>
            <AreaSummary bbox={bbox} />
          </Step>

          <Step n={2} title="Pick two dates" done={ready && Boolean(before)}>
            <DateSelect
              id="before"
              label="Earlier date"
              dates={dates.dates}
              value={before}
              onChange={setBefore}
              includeLatest={false}
              loading={dates.loading}
            />
            <DateSelect id="after" label="Later date" dates={dates.dates} value={after} onChange={setAfter} loading={dates.loading} />
            {dates.error && <p className="note note-warn">{dates.error}</p>}
            <p className="hint">The map shows the earlier date, so you can check the imagery before comparing.</p>
          </Step>

          <Step n={3} title="Compare" done={Boolean(result)}>
            {modelMissing && (
              <p className="note note-warn">Change detection needs the U-Net++ model. Load it in the backend first.</p>
            )}
            <button type="button" className="btn btn-primary btn-block" onClick={compare} disabled={!canRun}>
              {busy ? "Comparing…" : "Compare dates"}
            </button>
            {busy && <Working>Downloading both images and mapping their land cover.</Working>}
            <ErrorNote error={error} />
          </Step>
        </aside>

        <AreaPicker bbox={bbox} onChange={setBbox} release={before ? Number(before) : null} />
      </div>

      {!result && !busy && (
        <Empty title="Changes appear here">
          Select an area and two dates, then press Compare dates. You will see where land cover changed and
          by how many hectares.
        </Empty>
      )}

      {result && (
        <section className="results" aria-label="Change results" ref={resultsRef}>
          <div className="results-head">
            <h2>
              {fmtDate(b.scene.date)} → {fmtDate(a.scene.date)}
            </h2>
            <p className="mono muted">{b.scene.area_ha} ha analysed</p>
          </div>

          <Stats
            items={[
              { label: "Area changed", value: result.changed_percent.toFixed(1), unit: "%", tone: "change" },
              { label: "Changed land", value: formatHa(result.changed_hectares) },
              {
                label: "Biggest transition",
                value: top ? `${classInfo(top.from_class).label} → ${classInfo(top.to_class).label}` : "None",
              },
              { label: "Transitions found", value: result.transitions.length },
            ]}
          />

          <div className="card strip-pair">
            <CompositionStrip coverage={b.segmentation.coverage} label={fmtDate(b.scene.date)} />
            <CompositionStrip coverage={a.segmentation.coverage} label={fmtDate(a.scene.date)} />
          </div>

          <div className="results-grid results-grid-even">
            <div className="card stack">
              <div className="tabs" role="tablist" aria-label="Comparison view">
                {[
                  ["image", "Satellite images"],
                  ["mask", "Land cover maps"],
                ].map(([k, label]) => (
                  <button
                    key={k}
                    type="button"
                    role="tab"
                    aria-selected={view === k}
                    className={`tab ${view === k ? "tab-active" : ""}`}
                    onClick={() => setView(k)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <BeforeAfter
                before={pick(b)}
                after={pick(a)}
                beforeLabel={fmtDate(b.scene.date)}
                afterLabel={fmtDate(a.scene.date)}
              />
              <p className="caption">{a.scene.attribution}</p>
            </div>
            <div className="card stack">
              <ImageViewer
                views={[{ key: "change", label: "Where it changed", src: result.change_map }]}
                caption="Changed pixels in the colour of their new class. Unchanged land is grey."
              />
            </div>
          </div>

          <div className="results-grid results-grid-even">
            <div className="stack">
              <h3 className="section-title">Biggest transitions</h3>
              {result.transitions.length === 0 ? (
                <p className="muted">No land-cover change above 0.05% of the area.</p>
              ) : (
                <ol className="transitions">
                  {result.transitions.map((t) => (
                    <li key={`${t.from_class}-${t.to_class}`}>
                      <span className="swatch" style={{ background: classInfo(t.from_class).color }} />
                      {classInfo(t.from_class).label}
                      <span className="arrow" aria-label="became">→</span>
                      <span className="swatch" style={{ background: classInfo(t.to_class).color }} />
                      {classInfo(t.to_class).label}
                      <span className="mono t-num">
                        {t.percent.toFixed(1)}% · {formatHa(t.hectares)}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
              <p className="note">
                Images from different dates can be slightly shifted or taken in different seasons, so thin
                changes along edges and shadows are often not real.
              </p>
            </div>
            <div className="stack">
              <h3 className="section-title">Coverage by class</h3>
              <CoverageTable coverage={a.segmentation.coverage} before={b.segmentation.coverage} />
            </div>
          </div>

          <div className="impact-pair">
            <div className="stack">
              <h3 className="section-title">{fmtDate(b.scene.date)}</h3>
              <ImpactPanel impact={b.impact} compact />
            </div>
            <div className="stack">
              <h3 className="section-title">{fmtDate(a.scene.date)}</h3>
              <ImpactPanel impact={a.impact} compact />
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
