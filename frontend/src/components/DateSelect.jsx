/** Imagery date dropdown. Value is a Wayback release id, or "" for the latest imagery. */
export default function DateSelect({ id, label, dates, value, onChange, includeLatest = true, loading }) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} disabled={loading}>
        {loading && <option>Finding available dates…</option>}
        {!loading && includeLatest && <option value="">Latest imagery</option>}
        {!loading && !includeLatest && !dates.length && <option value="">Select an area first</option>}
        {!loading &&
          dates.map((d) => (
            <option key={d.release} value={d.release}>
              {new Date(d.date).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" })}
            </option>
          ))}
      </select>
    </div>
  );
}
