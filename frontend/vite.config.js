import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// SPA dev server. API calls are proxied to the Flask backend on :8000.
const api = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  // Built assets are served by Flask under /app/ (see the `spa` route in app.py),
  // alongside the server-rendered Jinja pages rather than replacing them.
  base: "/app/",
  server: {
    port: 5173,
    proxy: {
      "/upload": api,
      "/process": api,
      "/results": api,
      "/downloads": api,
      "/allvsall_status": api,
      "/allvsall_data": api,
      "/clustergram": api,
      "/embedding": api,
      "/health": api,
      "/tools": api, // POST endpoints: tree_construct, tree_status, tree_viewer, allvsall
    },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
