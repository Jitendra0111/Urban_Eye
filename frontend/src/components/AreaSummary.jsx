import { describeBbox, formatCoord, formatHa, formatMeters } from "../geo";

/** Readout of the selected area: corners, size and the resolution the analysis will use. */
export default function AreaSummary({ bbox }) {
  if (!bbox) {
    return (
      <p className="muted">
        No area yet. Use <strong>Draw area</strong> on the map, or zoom to a neighbourhood and press{" "}
        <strong>Use this view</strong>.
      </p>
    );
  }
  const info = describeBbox(bbox);
  const [w, s, e, n] = bbox;
  return (
    <div className="area-summary">
      <dl className="readout">
        <div>
          <dt>NW corner</dt>
          <dd>{formatCoord(n, "N", "S")} {formatCoord(w, "E", "W")}</dd>
        </div>
        <div>
          <dt>SE corner</dt>
          <dd>{formatCoord(s, "N", "S")} {formatCoord(e, "E", "W")}</dd>
        </div>
        <div>
          <dt>Size</dt>
          <dd>
            {formatMeters(info.widthM)} × {formatMeters(info.heightM)} · {formatHa(info.areaHa)}
          </dd>
        </div>
        <div>
          <dt>Resolution</dt>
          <dd>{info.resolution ? `${info.resolution.toFixed(2)} m per pixel` : "—"}</dd>
        </div>
      </dl>
      {info.tooSmall && <p className="note note-warn">Area too small. Make it at least about 50 m across.</p>}
      {!info.zoom && (
        <p className="note note-warn">Area too large. Draw a smaller area, up to about 4 km across.</p>
      )}
      {info.zoom && info.zoom < 18 && (
        <p className="note">
          This large area will be analysed at {info.resolution.toFixed(1)} m per pixel. The model was
          trained on 0.25–0.5 m imagery, so results are most accurate for areas under about 1 km across.
        </p>
      )}
    </div>
  );
}

export const bboxReady = (bbox) => {
  if (!bbox) return false;
  const info = describeBbox(bbox);
  return Boolean(info.zoom) && !info.tooSmall;
};
