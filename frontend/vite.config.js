import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, /api requests are forwarded to the FastAPI backend, so no CORS setup is needed.
// 127.0.0.1 rather than localhost: Node 18+ may resolve localhost to IPv6 (::1), but uvicorn
// listens on IPv4 127.0.0.1 by default.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": process.env.VITE_BACKEND_URL || "http://127.0.0.1:8000" },
  },
});
