import { useState } from "react";

/** Drag the handle to wipe between the earlier and later image of the same area. */
export default function BeforeAfter({ before, after, beforeLabel, afterLabel }) {
  const [pos, setPos] = useState(50);
  return (
    <div className="ba" style={{ "--pos": `${pos}%` }}>
      <img src={before} alt={beforeLabel} className="ba-img" />
      <img src={after} alt={afterLabel} className="ba-img ba-after" />
      <span className="ba-line" aria-hidden="true" />
      <span className="ba-tag ba-tag-left">{beforeLabel}</span>
      <span className="ba-tag ba-tag-right">{afterLabel}</span>
      <input
        type="range"
        min="0"
        max="100"
        value={pos}
        onChange={(e) => setPos(Number(e.target.value))}
        className="ba-range"
        aria-label="Compare earlier and later image"
      />
    </div>
  );
}
