import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import CompositionStrip from "../components/CompositionStrip";
import { Empty, ErrorNote, Working } from "../components/Feedback";
import { PageHead } from "../components/Layout";
import { IMPACT_LEVELS } from "../classes";
import { formatCoord, formatHa } from "../geo";

const PAGE = 12;
const FILTERS = [
  ["", "All"],
  ["analysis", "Area analyses"],
  ["comparison", "Comparisons"],
];

const imageryDate = (d) =>
  d === "latest" ? "Latest imagery" : new Date(d).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
const savedAt = (iso) => new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });

function HistoryCard({ item, onDelete, deleting }) {
  const level = IMPACT_LEVELS[item.level] ?? IMPACT_LEVELS.unknown;
  const isChange = item.kind === "comparison";
  const [w, s, e, n] = item.bbox;
  return (
    <li className="history-card">
      <div className="history-top">
        <span className={`kind kind-${item.kind}`}>{isChange ? "Change comparison" : "Area analysis"}</span>
        <span className="mono muted">{savedAt(item.created_at)}</span>
      </div>
      <h2 className="history-title">
        {isChange ? `${imageryDate(item.date)} → ${imageryDate(item.date_after)}` : imageryDate(item.date)}
      </h2>
      <p className="mono muted history-place">
        {formatCoord((s + n) / 2, "N", "S")} {formatCoord((w + e) / 2, "E", "W")} · {formatHa(item.area_ha)}
      </p>
      <CompositionStrip coverage={item.coverage} size="sm" />
      <dl className="history-figures">
        {isChange && (
          <div>
            <dt>Changed</dt>
            <dd className="changed">{item.changed_percent.toFixed(1)}%</dd>
          </div>
        )}
        <div>
          <dt>Green</dt>
          <dd>{item.green_score.toFixed(1)}</dd>
        </div>
        <div>
          <dt>Urban</dt>
          <dd>{item.urban_score.toFixed(1)}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd className={`tone-text-${level.tone}`}>{level.label}</dd>
        </div>
      </dl>
      <div className="history-actions">
        <Link to={`${isChange ? "/change" : "/map"}?saved=${item.id}`} className="btn btn-small btn-primary">
          Open
        </Link>
        <button type="button" className="btn btn-small btn-quiet" onClick={() => onDelete(item)} disabled={deleting}>
          {deleting ? "Deleting…" : "Delete"}
        </button>
      </div>
    </li>
  );
}

export default function History() {
  const [kind, setKind] = useState("");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleting, setDeleting] = useState(null);

  async function load(offset = 0) {
    setLoading(true);
    setError(null);
    try {
      const page = await api.history({ kind, limit: PAGE, offset });
      setItems((prev) => (offset ? [...prev, ...page.items] : page.items));
      setTotal(page.total);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(0);
  }, [kind]); // eslint-disable-line react-hooks/exhaustive-deps

  async function remove(item) {
    if (!window.confirm("Delete this saved result? This cannot be undone.")) return;
    setDeleting(item.id);
    try {
      await api.deleteHistory(item.id);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
      setTotal((t) => t - 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="page">
      <PageHead
        title="History"
        aside={!loading && <span className="mono muted">{total} saved result{total === 1 ? "" : "s"}</span>}
      >
        Every area analysis and comparison is saved. Open one to see it again instantly, without re-running the model.
      </PageHead>

      <div className="tabs" role="tablist" aria-label="Filter saved results">
        {FILTERS.map(([k, label]) => (
          <button
            key={k || "all"}
            type="button"
            role="tab"
            aria-selected={kind === k}
            className={`tab ${kind === k ? "tab-active" : ""}`}
            onClick={() => setKind(k)}
          >
            {label}
          </button>
        ))}
      </div>

      <ErrorNote error={error} />

      {!loading && !error && items.length === 0 && (
        <Empty title="No saved results yet">
          Results are saved automatically. Run a <Link to="/map">map analysis</Link> or{" "}
          <Link to="/change">compare two dates</Link> and it will appear here.
        </Empty>
      )}

      {items.length > 0 && (
        <ul className="history-grid">
          {items.map((item) => (
            <HistoryCard key={item.id} item={item} onDelete={remove} deleting={deleting === item.id} />
          ))}
        </ul>
      )}

      {loading && <Working>Loading saved results.</Working>}
      {!loading && items.length < total && (
        <button type="button" className="btn history-more" onClick={() => load(items.length)}>
          Show more
        </button>
      )}
    </div>
  );
}
