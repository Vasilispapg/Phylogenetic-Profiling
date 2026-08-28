import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// SPA dev server. API calls are proxied to the Flask backend on :8000.
const api = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Every endpoint is under /api, so one rule covers the whole backend.
    proxy: { "/api": api },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
