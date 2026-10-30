import { useEffect, useRef } from "react";

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
