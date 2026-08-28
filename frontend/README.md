# PhyloFlask — React frontend

A **Vite + React** single-page app that consumes the existing **Flask JSON API**
(`../app.py`). The Python backend still does all the heavy lifting (BLAST parsing,
NJ trees via biopython, MCL via networkx, pandas/scipy); React only renders the UI.

## Develop
Two terminals:

```bash
# 1) backend (analysis + JSON API) on :8000
cd ..
source .venv/bin/activate && python app.py

# 2) frontend (Vite dev server) on :5173, proxies API calls to :8000
cd frontend
npm install
npm run dev          # open http://localhost:5173
```

API paths (`/upload`, `/process`, `/downloads`, `/tools/*`, `/allvsall_*`,
`/clustergram`, `/embedding`, `/health`) are proxied to Flask by `vite.config.js`.

## Test & build
```bash
npm run test         # vitest (src/lib/matrix.test.js)
npm run build        # → frontend/dist/, served by Flask at /app
npm run preview      # preview the production build
```
The bundle is built with `base: "/app/"` and the router with a matching
`basename`, because Flask mounts it at `/app` alongside the Jinja pages. The
Docker image builds it in its first stage.

## Structure
```
src/
  main.jsx, App.jsx          entry + routing (heavy viz pages are code-split)
  theme.css                  the design system (mirrors ../docs/DESIGN.md)
  lib/api.js                 fetch helpers (upload / poll / postJSON)
  components/                Layout (navbar+footer), Dropzone, Stepper, Status, Molecule
  pages/                     Landing, Blast, TreeBuilder, TreeViewer, AllVsAll, Heatmap,
                             Clustergram, Explorer, Embedding, HowTo, Faq, StyleGuide
```

Design tokens/components follow [`../docs/DESIGN.md`](../docs/DESIGN.md); the live
gallery is at `/styleguide`.
