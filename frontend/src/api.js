// All calls to the UrbanEye FastAPI backend.
const BASE = import.meta.env.VITE_API_URL || "";

const OFFLINE =
  "Can't reach the UrbanEye backend. Start it in the backend folder with: uvicorn app.main:app --port 8000";

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, options);
  } catch {
    throw new Error(OFFLINE);
  }
  if (res.status === 502 && !res.headers.get("content-type")?.includes("json")) {
    throw new Error(OFFLINE); // Vite proxy answers 502 when the backend is down
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg).join("; ")
      : detail || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return body;
}

const postJson = (path, data) =>
  request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

const postFile = (path, file) => {
  const form = new FormData();
  form.append("file", file);
  return request(path, { method: "POST", body: form });
};

export const api = {
  health: () => request("/api/health"),
  dates: (lat, lon) => request(`/api/satellite/dates?lat=${lat}&lon=${lon}`),
  analyzeArea: (body) => postJson("/api/satellite/analyze", body),
  compare: (body) => postJson("/api/satellite/compare", body),
  segment: (file) => postFile("/api/segment", file),
  detect: (file) => postFile("/api/detect", file),
  impact: (file) => postFile("/api/environmental-impact", file),
  history: ({ kind = "", limit = 20, offset = 0 } = {}) =>
    request(`/api/history?limit=${limit}&offset=${offset}${kind ? `&kind=${kind}` : ""}`),
  historyEntry: (id) => request(`/api/history/${id}`),
  deleteHistory: (id) => request(`/api/history/${id}`, { method: "DELETE" }),
};
