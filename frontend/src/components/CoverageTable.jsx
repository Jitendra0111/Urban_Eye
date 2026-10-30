import { CLASSES, classInfo } from "../classes";
import { formatHa } from "../geo";

/** Coverage per class. With areaHa, also shows real area; with `before`, shows the change. */
export default function CoverageTable({ coverage, areaHa, before }) {
  const keys = CLASSES.some((c) => c.key in coverage)
    ? CLASSES.map((c) => c.key)
    : Object.keys(coverage); // detector class names when no segmentation model is loaded
  const rows = keys
    .map((key) => ({ ...classInfo(key), pct: coverage[key] ?? 0, was: before?.[key] ?? 0 }))
    .filter((r) => r.pct > 0 || r.was > 0)
    .sort((a, b) => b.pct - a.pct);

  return (
    <div className="table-wrap">
      <table className="coverage-table">
        <thead>
          <tr>
            <th scope="col">Class</th>
            {before && <th scope="col" className="num">Before</th>}
            <th scope="col" className="num">{before ? "After" : "Share"}</th>
            {before && <th scope="col" className="num">Change</th>}
            {areaHa != null && <th scope="col" className="num">Area</th>}
            <th scope="col" className="bar-col"><span className="sr-only">Share bar</span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const delta = r.pct - r.was;
            return (
              <tr key={r.key}>
                <th scope="row">
                  <span className="swatch" style={{ background: r.color }} />
                  {r.label}
                </th>
                {before && <td className="num">{r.was.toFixed(1)}%</td>}
                <td className="num">{r.pct.toFixed(1)}%</td>
                {before && (
                  <td className={`num delta ${delta > 0.05 ? "up" : delta < -0.05 ? "down" : ""}`}>
                    {delta > 0 ? "+" : ""}
                    {delta.toFixed(1)}
                  </td>
                )}
                {areaHa != null && <td className="num">{formatHa((r.pct * areaHa) / 100)}</td>}
                <td className="bar-col">
                  <span className="bar" style={{ width: `${Math.min(100, r.pct)}%`, background: r.color }} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
