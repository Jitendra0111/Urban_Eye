import { CLASSES } from "../classes";

/**
 * The land as one bar: each class takes a share of the width equal to its coverage.
 * Read left to right like a core sample of the area.
 */
export default function CompositionStrip({ coverage, label, size = "md" }) {
  const total = CLASSES.reduce((sum, c) => sum + (coverage[c.key] ?? 0), 0) || 1;
  const parts = CLASSES.map((c) => ({ ...c, pct: coverage[c.key] ?? 0 })).filter((c) => c.pct > 0);
  const summary = parts.map((p) => `${p.label} ${p.pct.toFixed(1)}%`).join(", ");

  return (
    <figure className={`strip strip-${size}`}>
      {label && <figcaption className="strip-label">{label}</figcaption>}
      <div className="strip-bar" role="img" aria-label={`Land cover: ${summary}`}>
        {parts.map((p) => (
          <span
            key={p.key}
            className="strip-seg"
            style={{ flexGrow: p.pct / total, background: p.color }}
            title={`${p.label}: ${p.pct.toFixed(1)}%`}
          >
            {p.pct >= 9 && size !== "sm" && (
              <span className={`strip-seg-text ${["road", "rangeland"].includes(p.key) ? "dark" : ""}`}>
                {p.pct.toFixed(0)}%
              </span>
            )}
          </span>
        ))}
      </div>
    </figure>
  );
}

export function Legend() {
  return (
    <ul className="legend">
      {CLASSES.map((c) => (
        <li key={c.key}>
          <span className="swatch" style={{ background: c.color }} />
          {c.label}
        </li>
      ))}
    </ul>
  );
}
