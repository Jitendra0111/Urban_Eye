import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import AreaPicker from "../components/AreaPicker";
import AreaSummary, { bboxReady } from "../components/AreaSummary";
import { Empty, ErrorNote } from "../components/Feedback";
import { PageHead, QualitySwitch, Stats, Step, useQuality, useRevealOn } from "../components/Layout";
import TimelineChart from "../components/TimelineChart";
import { CLASSES } from "../classes";
import { useAreaDates, useHealth } from "../hooks";

const COUNTS = [4, 6, 8, 12];
const fmtDate = (d) => new Date(d).toLocaleDateString("en-IN", { year: "numeric", month: "short" });

/** n dates spread evenly from the oldest to the newest (dates arrive newest first). */
function pickDates(dates, n) {
  const asc = [...dates].reverse();
  if (asc.length <= n) return asc;
  const idx = new Set(Array.from({ length: n }, (_, i) => Math.round((i * (asc.length - 1)) / (n - 1))));
  return [...idx].map((i) => asc[i]);
}

function biggestShift(points) {
  const first = points[0].coverage;
  const last = points.at(-1).coverage;
  const deltas = CLASSES.map((c) => ({ ...c, d: (last[c.key] ?? 0) - (first[c.key] ?? 0) }));
  deltas.sort((a, b) => b.d - a.d);
  return { gain: deltas[0], loss: deltas.at(-1) };
}

export default function Timeline() {
  const { health } = useHealth();
  const [bbox, setBbox] = useState(null);
  const [count, setCount] = useState(6);
  const [quality, setQuality] = useQuality();
  const [points, setPoints] = useState([]);
  const [progress, setProgress] = useState(null); // { done, total, current }
  const [errors, setErrors] = useState([]);
  const stop = useRef(false);
  const dates = useAreaDates(bbox);
  const finished = progress && progress.done === progress.total && points.length > 0;
  const resultsRef = useRevealOn(finished ? points.length : 0);

  const ready = bboxReady(bbox);
  const busy = progress != null && progress.done < progress.total && !progress.stopped;
  const chosen = pickDates(dates.dates, count);
  const modelMissing = health && !health.segmentation_model;

  async function run() {
    stop.current = false;
    setPoints([]);
    setErrors([]);
    const list = chosen;
    const collected = [];
    for (let i = 0; i < list.length; i++) {
      if (stop.current) {
        setProgress({ done: i, total: list.length, stopped: true });
        return;
      }
      setProgress({ done: i, total: list.length, current: list[i].date });
      try {
        const r = await api.analyzeArea({ bbox, release: list[i].release, detect: false, quality });
        collected.push({
          t: new Date(r.scene.date === "latest" ? list[i].date : r.scene.date).getTime(),
          date: r.scene.date === "latest" ? list[i].date : r.scene.date,
          coverage: r.impact.coverage,
          green_score: r.impact.green_score,
          urban_score: r.impact.urban_score,
          saved_id: r.saved_id,
          cached: r.cached,
        });
        collected.sort((a, b) => a.t - b.t);
        setPoints([...collected]);
      } catch (e) {
        setErrors((prev) => [...prev, `${fmtDate(list[i].date)}: ${e.message}`]);
      }
    }
    setProgress({ done: list.length, total: list.length });
  }

  const shift = points.length >= 2 ? biggestShift(points) : null;

  return (
    <div className="page">
      <PageHead title="Timeline">
        See how the land cover of one area changed across many imagery dates since 2014.
      </PageHead>

      <div className="workbench">
        <aside className="panel" aria-label="Timeline settings">
          <Step n={1} title="Choose an area" done={ready}>
            <AreaSummary bbox={bbox} />
          </Step>

          <Step n={2} title="Choose how many dates" done={ready && chosen.length >= 2}>
            <div className="field">
              <label htmlFor="count">Dates to analyse</label>
              <select id="count" value={count} onChange={(e) => setCount(Number(e.target.value))} disabled={busy}>
                {COUNTS.map((n) => (
                  <option key={n} value={n}>
                    {n} dates
                  </option>
                ))}
              </select>
            </div>
            {dates.loading && <p className="hint">Finding available dates…</p>}
            {dates.error && <p className="note note-warn">{dates.error}</p>}
            {bbox && !dates.loading && chosen.length > 0 && (
              <p className="hint">
                {dates.dates.length} dates available here. Analysing {chosen.length}, spread from{" "}
                {fmtDate(chosen[0].date)} to {fmtDate(chosen.at(-1).date)}.
              </p>
            )}
          </Step>

          <Step n={3} title="Build the timeline" done={Boolean(finished)}>
            <QualitySwitch value={quality} onChange={setQuality} disabled={busy} />
            {modelMissing && (
              <p className="note note-warn">The timeline needs the U-Net++ model. Load it in the backend first.</p>
            )}
            {busy ? (
              <button type="button" className="btn btn-block" onClick={() => (stop.current = true)}>
                Stop after this date
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary btn-block"
                onClick={run}
                disabled={!ready || chosen.length < 2 || modelMissing}
              >
                Build timeline
              </button>
            )}
            {progress && progress.total > 0 && (
              <div className="progress" role="status">
                <div className="progress-bar">
                  <span style={{ width: `${(progress.done / progress.total) * 100}%` }} />
                </div>
                <p className="hint">
                  {busy
                    ? `Analysing date ${progress.done + 1} of ${progress.total} (${fmtDate(progress.current)})…`
                    : progress.stopped
                      ? `Stopped after ${progress.done} of ${progress.total} dates.`
                      : `Done: ${progress.total} dates. Already-analysed dates load instantly from the database.`}
                </p>
              </div>
            )}
            {errors.map((e) => (
              <ErrorNote key={e} error={e} />
            ))}
          </Step>
        </aside>

        <AreaPicker bbox={bbox} onChange={setBbox} />
      </div>

      {points.length < 2 && !busy && (
        <Empty title="The timeline appears here">
          Select an area, choose how many dates, and press Build timeline. Each date is a full land-cover
          analysis, so 6 dates take about 1–2 minutes the first time and are instant afterwards.
        </Empty>
      )}

      {points.length >= 2 && (
        <section className="results" aria-label="Timeline results" ref={resultsRef}>
          <div className="results-head">
            <h2>
              {fmtDate(points[0].date)} → {fmtDate(points.at(-1).date)}
            </h2>
            <p className="mono muted">
              {points.length} dates · {quality} mode
            </p>
          </div>

          <Stats
            items={[
              { label: "Period", value: `${new Date(points.at(-1).t).getFullYear() - new Date(points[0].t).getFullYear()} years` },
              {
                label: "Biggest gain",
                value: shift.gain.d > 0 ? `${shift.gain.label} +${shift.gain.d.toFixed(1)} pts` : "None",
              },
              {
                label: "Biggest loss",
                value: shift.loss.d < 0 ? `${shift.loss.label} ${shift.loss.d.toFixed(1)} pts` : "None",
                tone: "change",
              },
              {
                label: "Green score change",
                value: `${points.at(-1).green_score - points[0].green_score >= 0 ? "+" : ""}${(points.at(-1).green_score - points[0].green_score).toFixed(1)}`,
                tone: "green",
              },
            ]}
          />

          <div className="card">
            <TimelineChart points={points} />
          </div>

          <div className="stack">
            <h3 className="section-title">Every date</h3>
            <div className="table-wrap">
              <table className="coverage-table timeline-table">
                <thead>
                  <tr>
                    <th scope="col">Date</th>
                    {CLASSES.map((c) => (
                      <th key={c.key} scope="col" className="num">
                        {c.label}
                      </th>
                    ))}
                    <th scope="col" className="num">Green</th>
                    <th scope="col" className="num">Urban</th>
                    <th scope="col"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {points.map((p) => (
                    <tr key={p.t}>
                      <th scope="row">{fmtDate(p.date)}</th>
                      {CLASSES.map((c) => (
                        <td key={c.key} className="num">{(p.coverage[c.key] ?? 0).toFixed(1)}%</td>
                      ))}
                      <td className="num">{p.green_score.toFixed(1)}</td>
                      <td className="num">{p.urban_score.toFixed(1)}</td>
                      <td className="row-actions">
                        {p.saved_id && (
                          <>
                            <Link to={`/map?saved=${p.saved_id}`}>Open</Link>
                            <a href={api.reportUrl(p.saved_id)} download>PDF</a>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="note">
              Imagery dates differ in season, sun angle and sensor, so small ups and downs between neighbouring
              dates are often not real change. Look for steady trends across several dates.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}
