// The 8 OpenEarthMap land-cover classes, in model output order, with the dataset's own colours
// (the backend draws its masks with the same colours).
export const CLASSES = [
  { key: "bareland", label: "Bareland", color: "#800000" },
  { key: "rangeland", label: "Rangeland", color: "#00ff24" },
  { key: "developed space", label: "Developed space", color: "#949494" },
  { key: "road", label: "Road", color: "#ffffff" },
  { key: "tree", label: "Tree", color: "#226126" },
  { key: "water", label: "Water", color: "#0045ff" },
  { key: "agriculture land", label: "Agriculture", color: "#4bb549" },
  { key: "building", label: "Building", color: "#de1f07" },
];

export const classInfo = (key) =>
  CLASSES.find((c) => c.key === key.toLowerCase()) ?? { key, label: key, color: "#8a9599" };

export const IMPACT_LEVELS = {
  healthy: { label: "Healthy", tone: "good" },
  balanced: { label: "Balanced", tone: "good" },
  warning: { label: "Unbalanced", tone: "warn" },
  danger: { label: "Urban pressure", tone: "bad" },
  critical: { label: "Critical", tone: "bad" },
  unknown: { label: "No features", tone: "neutral" },
};
