import { useState } from "react";
import { CLASSES } from "../classes";

// Small multiples: one panel per land-cover class, all on the same 0–max scale, so panels can be
// compared at a glance and identity comes from the panel title, not from telling colours apart.
// Line colours follow the map legend; the two that are invisible on white get a darker stroke.
const LINE_COLOUR = { road: "#6b7680", rangeland: "#13a538" };

const W = 300;
const H = 150;
const PAD = { top: 12, right: 14, bottom: 24, left: 34 };

const fmtMonth = (t) => new Date(t).toLocaleDateString("en-IN", { year: "numeric", month: "short" });

function scales(points, yMax) {
  const t0 = points[0].t;
  const t1 = points.at(-1).t;
  const span = t1 - t0 || 1;
  const x = (t) => PAD.left + ((t - t0) / span) * (W - PAD.left - PAD.right);
  const y = (v) => PAD.top + (1 - v / yMax) * (H - PAD.top - PAD.bottom);
  return { x, y };
}

function yearTicks(points) {
  const first = new Date(points[0].t).getFullYear();
  const last = new Date(points.at(-1).t).getFullYear();
  if (first === last) return [points[0].t];
  const mid = Math.round((first + last) / 2);
  return [...new Set([first, mid, last])].map((yr) => Date.UTC(yr, 0, 1)).filter(
    (t) => t >= points[0].t - 3e10 && t <= points.at(-1).t + 3e10,
  );
}

/** One small panel: a single series (or a few, for the score chart) over time with hover readout. */
function Panel({ title, series, points, yMax, unit = "%", note }) {
  const [hover, setHover] = useState(null);
  const { x, y } = scales(points, yMax);
  const ticks = [0, yMax / 2, yMax];

  return (
    <figure className="tl-panel">
      <figcaption className="tl-title">
        {series.length === 1 && <span className="swatch" style={{ background: series[0].swatch }} />}
        {title}
        {note && <span className="tl-note">{note}</span>}
      </figcaption>
      <div className="tl-plot">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title} over time`}>
          {ticks.map((v) => (
            <g key={v}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} className="tl-grid" />
              <text x={PAD.left - 6} y={y(v) + 3.5} className="tl-axis" textAnchor="end">
                {Math.round(v)}
              </text>
            </g>
          ))}
          {yearTicks(points).map((t) => (
            <text key={t} x={x(Math.min(Math.max(t, points[0].t), points.at(-1).t))} y={H - 6}
              className="tl-axis" textAnchor="middle">
              {new Date(t).getFullYear()}
            </text>
          ))}
          {hover != null && (
            <line x1={x(points[hover].t)} x2={x(points[hover].t)} y1={PAD.top} y2={H - PAD.bottom}
              className="tl-cross" />
          )}
          {series.map((s) => (
            <g key={s.key}>
              <polyline
                points={points.map((p, i) => `${x(p.t)},${y(s.values[i])}`).join(" ")}
                fill="none" stroke={s.colour} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round"
              />
              {points.map((p, i) => (
                <circle key={p.t} cx={x(p.t)} cy={y(s.values[i])} r={hover === i ? 5 : 4}
                  fill={s.colour} stroke="var(--panel)" strokeWidth="2" />
              ))}
            </g>
          ))}
          {/* Hit areas wider than the marks: one column per date. */}
          {points.map((p, i) => {
            const left = i === 0 ? PAD.left : (x(points[i - 1].t) + x(p.t)) / 2;
            const right = i === points.length - 1 ? W - PAD.right : (x(p.t) + x(points[i + 1].t)) / 2;
            return (
              <rect key={p.t} x={left} y={PAD.top} width={Math.max(1, right - left)} height={H - PAD.top - PAD.bottom}
                fill="transparent" onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} />
            );
          })}
        </svg>
        {hover != null && (
          <div className="tl-tip" style={{ left: `${(x(points[hover].t) / W) * 100}%` }} role="status">
            <strong>{fmtMonth(points[hover].t)}</strong>
            {series.map((s) => (
              <span key={s.key}>
                {series.length > 1 && <span className="swatch" style={{ background: s.swatch }} />}
                {series.length > 1 ? `${s.label} ` : ""}
                {s.values[hover].toFixed(1)}
                {unit}
              </span>
            ))}
          </div>
        )}
      </div>
    </figure>
  );
}

/**
 * points: [{ t: ms timestamp, coverage: {class: %}, green_score, urban_score }], sorted by date.
 */
export default function TimelineChart({ points }) {
  const present = CLASSES.filter((c) => points.some((p) => (p.coverage[c.key] ?? 0) >= 0.5));
  const hidden = CLASSES.filter((c) => !present.includes(c));
  const max = Math.max(...present.flatMap((c) => points.map((p) => p.coverage[c.key] ?? 0)), 1);
  const yMax = Math.ceil(max / 10) * 10;

  return (
    <div className="tl">
      <div className="tl-grid-panels">
        {present.map((c) => {
          const values = points.map((p) => p.coverage[c.key] ?? 0);
          const delta = values.at(-1) - values[0];
          return (
            <Panel
              key={c.key}
              title={c.label}
              note={`${delta >= 0 ? "+" : ""}${delta.toFixed(1)} pts`}
              points={points}
              yMax={yMax}
              series={[{ key: c.key, label: c.label, values, colour: LINE_COLOUR[c.key] ?? c.color, swatch: c.color }]}
            />
          );
        })}
      </div>
      <p className="caption">
        Share of the area (%) per class, all panels on the same 0–{yMax}% scale. Hover a panel to read each date.
        {hidden.length > 0 && ` Not shown (under 0.5% at every date): ${hidden.map((c) => c.label).join(", ")}.`}
      </p>

      <div className="tl-scores">
        <Panel
          title="Environmental scores"
          points={points}
          yMax={100}
          unit=""
          series={[
            { key: "green", label: "Green", values: points.map((p) => p.green_score), colour: "#226126", swatch: "#226126" },
            { key: "urban", label: "Urban", values: points.map((p) => p.urban_score), colour: "#de1f07", swatch: "#de1f07" },
          ]}
        />
        <ul className="legend tl-legend">
          <li>
            <span className="swatch" style={{ background: "#226126" }} />
            Green score {points.at(-1).green_score.toFixed(1)}
          </li>
          <li>
            <span className="swatch" style={{ background: "#de1f07" }} />
            Urban score {points.at(-1).urban_score.toFixed(1)}
          </li>
        </ul>
      </div>
    </div>
  );
}
