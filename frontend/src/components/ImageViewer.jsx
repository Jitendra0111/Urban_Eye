import { useState } from "react";

/** One image area with tabs to switch between views of the same scene. */
export default function ImageViewer({ views, caption }) {
  const available = views.filter((v) => v.src);
  const [active, setActive] = useState(available[0]?.key);
  const current = available.find((v) => v.key === active) ?? available[0];
  if (!current) return null;

  return (
    <figure className="viewer">
      {available.length > 1 && (
        <div className="tabs" role="tablist" aria-label="Image view">
          {available.map((v) => (
            <button
              key={v.key}
              type="button"
              role="tab"
              aria-selected={v.key === current.key}
              className={`tab ${v.key === current.key ? "tab-active" : ""}`}
              onClick={() => setActive(v.key)}
            >
              {v.label}
            </button>
          ))}
        </div>
      )}
      <div className="viewer-frame">
        <img src={current.src} alt={current.alt ?? current.label} />
      </div>
      {caption && <figcaption className="caption">{caption}</figcaption>}
    </figure>
  );
}
