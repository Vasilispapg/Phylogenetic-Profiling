import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// SPA dev server. API calls are proxied to the Flask backend on :8000.
const api = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
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
      "/tools": api, // POST endpoints: tree_construct, tree_status, tree_viewer, allvsall
    },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
