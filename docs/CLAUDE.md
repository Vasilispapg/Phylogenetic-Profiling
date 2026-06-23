# CLAUDE.md

Agent onboarding for this repo. Read this first; for a file map see
[`INDEX.md`](INDEX.md) and for architecture/methods see
[`CODE_ANALYSIS.md`](CODE_ANALYSIS.md). You should rarely need to read the whole
codebase.

## What this is
**PhyloFlask** — a Flask web app + CLI for **phylogenetic profiling** of protein domains: parse a
BLAST file → species × domain presence/absence matrices → Neighbour-Joining
species tree (Jaccard) and domain clusters (MCL) with a validation report, plus
browser heatmaps and an all-vs-all graph.

## Environment & commands
- **Python 3.13**, virtualenv at `.venv` (in the repo, on the T7 drive).
  - `source .venv/bin/activate`
  - `pip install -r requirements.txt`
- **Run web (dev):** `python app.py` → http://127.0.0.1:8000
  - Default port is **8000**, not 5000: macOS AirPlay Receiver owns 5000/7000
    (answers `Server: AirTunes`) and makes the app look broken. Override with `PORT`.
- **Run both dev servers (React UI):** `./dev.sh` → Flask API :8000 + Vite React
  :5173 (proxied). The React SPA in `frontend/` is the primary UI; `npm run dev`
  alone starts only the frontend and its API calls fail — start the backend too.
- **Run web (prod):** `gunicorn --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:8000 app:app`
- **Docker:** `docker compose up --build` → http://localhost:8000
- **Tests:** `pytest -q` (28 tests)
- **CLI:** `python main.py --analyze | --construct_tree | --validate_clusters | ...`

## Must-know conventions & gotchas
- **gunicorn must run with 1 worker.** Job state (`_jobs`, `precomputed_results`)
  is in-memory; multiple workers would not share it. Threads handle concurrency.
- **`analysis/utils.extract_species` is the single source of truth** for the
  species key (first 4 dash-segments of `SubjectID`). Use it everywhere so the
  correlation and feature matrices stay aligned. Don't reintroduce per-call regexes.
- **Presence = `EValue <= 1e-5`** in `create_correlation_matrix(evalue_threshold=...)`.
- **Tree distances come from the correlation matrix** (Jaccard between domain
  profiles → NJ), *not* from `data/list.2`. Tree-construct input is a correlation
  matrix CSV.
- **Clustering is domain × domain** (`cluster_domains`), not the raw bipartite
  species–domain graph. Validate with `validate_clusters` / `--validate_clusters`.
- **The bundled dataset has no real cluster structure** (modularity ≈ 0, one
  dominant cluster). That is the data, not a bug — `validate_clusters` flags it.
  Don't "fix" it by tweaking code; it needs richer/sharper data.
- **NJ is O(n³).** ~600 species ≈ 1 min; ~3000 would take hours.
- **`BiopythonWarning: importing Biopython from inside the source tree`** is
  benign (biopython is installed under `.venv` in the repo). Ignore it.
- **Don't commit generated data.** `output/`, `downloads/`, `uploads/`, `cache/`,
  `.venv/` are gitignored. `data/` sample inputs are intentionally tracked.
- **Flask debug is off by default**; enable with `FLASK_DEBUG=1` (never in prod).
  Host defaults to `127.0.0.1`.

## Where to make changes
- New analysis → `analysis/`. New page/route → the matching `templates/*.py`
  blueprint + a `pages/*.html` that `{% extends "tools.html" %}`.
- Nav links use **blueprint-qualified** `url_for` (e.g. `tree.tree_viewer_tool`).
- **React tools** live in `frontend/src/pages/*.jsx` (Clustergram, Explorer,
  Embedding, …); shared CSV/transform helpers in `frontend/src/lib/matrix.js`,
  fetch helpers in `frontend/src/lib/api.js`. `heatmap_bp` also serves
  `POST /clustergram` (SciPy hierarchical clustering) and `POST /embedding`
  (scikit-learn PCA/t-SNE + KMeans) — both take the numeric matrix as JSON.
- Add tests under `tests/` (pytest; `conftest.py` puts the repo root on `sys.path`).

## Git
Active work branch: `fix/audit-remediation`. Branch off it; commit only when asked.
