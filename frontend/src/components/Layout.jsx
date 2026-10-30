import { useEffect, useRef, useState } from "react";
import { api } from "../api";

/** Page title row: title and one-line description on the left, optional extra content on the right. */
export function PageHead({ title, children, aside }) {
  return (
    <header className="page-head">
      <div>
        <h1>{title}</h1>
        {children && <p className="muted">{children}</p>}
      </div>
      {aside}
    </header>
  );
}

/** One numbered step of a workflow panel. `done` ticks the number once the step is complete. */
export function Step({ n, title, done = false, children }) {
  return (
    <section className={`step ${done ? "step-done" : ""}`} aria-label={`Step ${n}: ${title}`}>
      <h2 className="step-title">
        <span className="step-num" aria-hidden="true">{done ? "✓" : n}</span>
        {title}
      </h2>
      <div className="step-body">{children}</div>
    </section>
  );
}

/** Row of headline numbers at the top of a result. items: [{ label, value, unit?, tone? }] */
export function Stats({ items }) {
  return (
    <dl className="stats">
      {items.map((s) => (
        <div key={s.label} className={`stat ${s.tone ? `stat-${s.tone}` : ""}`}>
          <dt>{s.label}</dt>
          <dd>
            {s.value}
            {s.unit && <span className="stat-unit">{s.unit}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** Scrolls the returned ref into view whenever `value` becomes truthy (e.g. a new result). */
export function useRevealOn(value) {
  const ref = useRef(null);
  useEffect(() => {
    if (value && ref.current) {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      ref.current.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    }
  }, [value]);
  return ref;
}

const savedAt = (iso) =>
  new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });

/** Shown on a result that came from the database instead of a fresh model run. */
export function SavedNote({ result, savedOn, onRerun, busy }) {
  if (!result?.cached) return null;
  return (
    <div className="saved-note" role="status">
      <span>
        <strong>Saved result</strong>
        {savedOn ? ` from ${savedAt(savedOn)}` : ""}, loaded instantly from the database.
      </span>
      {onRerun && (
        <button type="button" className="btn btn-small" onClick={onRerun} disabled={busy}>
          {busy ? "Running…" : "Run again"}
        </button>
      )}
    </div>
  );
}

const QUALITY_KEY = "urbaneye.quality";

/** The Fast / Accurate choice, remembered in this browser. */
export function useQuality() {
  const [quality, setQuality] = useState(() => {
    try {
      return localStorage.getItem(QUALITY_KEY) === "accurate" ? "accurate" : "fast";
    } catch {
      return "fast";
    }
  });
  const choose = (q) => {
    setQuality(q);
    try {
      localStorage.setItem(QUALITY_KEY, q);
    } catch {
      // Storage blocked: the choice still applies on this page.
    }
  };
  return [quality, choose];
}

const QUALITY_OPTIONS = [
  { value: "fast", label: "Fast", hint: "One model pass. About twice as fast." },
  { value: "accurate", label: "Accurate", hint: "Averages the image and its mirror image. Slightly cleaner maps." },
];

export function QualitySwitch({ value, onChange, disabled }) {
  const current = QUALITY_OPTIONS.find((o) => o.value === value) ?? QUALITY_OPTIONS[0];
  return (
    <fieldset className="quality" disabled={disabled}>
      <legend>Model mode</legend>
      <div className="segmented" role="radiogroup">
        {QUALITY_OPTIONS.map((o) => (
          <label key={o.value} className={`segmented-option ${value === o.value ? "is-on" : ""}`}>
            <input
              type="radio"
              name="quality"
              value={o.value}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
            />
            {o.label}
          </label>
        ))}
      </div>
      <p className="hint">{current.hint}</p>
    </fieldset>
  );
}

/** Download link for the PDF report of a saved result. */
export function ReportButton({ savedId, className = "btn btn-small" }) {
  if (!savedId) return null;
  return (
    <a className={className} href={api.reportUrl(savedId)} download>
      Download PDF report
    </a>
  );
}
