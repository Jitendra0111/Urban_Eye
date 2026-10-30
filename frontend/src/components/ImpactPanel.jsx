import { IMPACT_LEVELS } from "../classes";

function Meter({ label, value, tone }) {
  return (
    <div className="meter">
      <div className="meter-head">
        <span>{label}</span>
        <span className="mono">{value.toFixed(1)}</span>
      </div>
      <div className="meter-track">
        <span className={`meter-fill ${tone}`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
    </div>
  );
}

/** Environmental impact verdict from /environmental-impact (same rules as the original app). */
export default function ImpactPanel({ impact, compact = false }) {
  const level = IMPACT_LEVELS[impact.level] ?? IMPACT_LEVELS.unknown;
  return (
    <section className={`impact tone-${level.tone}`} aria-label="Environmental impact">
      <div className="impact-head">
        <span className="badge">{level.label}</span>
        <p className="impact-status">{impact.status}</p>
      </div>
      <Meter label="Green score" value={impact.green_score} tone="green" />
      <Meter label="Urban score" value={impact.urban_score} tone="urban" />
      {!compact && (
        <>
          <h4>Recommendations</h4>
          <ul className="recs">
            {impact.recommendations.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </>
      )}
      {impact.source === "detection" && (
        <p className="note">
          Estimated from detection boxes because the U-Net++ model is not loaded. Areas are approximate.
        </p>
      )}
    </section>
  );
}
