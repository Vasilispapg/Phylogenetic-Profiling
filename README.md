# PhyloFlask

**PhyloFlask** — a software framework for large-scale **phylogenetic profile
visualization**. A Flask web app (with a parallel CLI) that turns a BLAST
tabular file into interactive species trees, domain clusters and heatmaps. It
builds species × domain presence/absence matrices and from them:

- a **Neighbour-Joining species tree** (Jaccard distance between domain profiles),
  shown in an interactive collapsible radial viewer (colour-by-genus, search),
- **domain clusters** (Markov Clustering) shown as an interactive network
  (colour-by-cluster, edge-weight slider, layout switcher) **linked** to a
  co-cluster heatmap, with a **clustering-quality validation report**,
- interactive **heatmaps**, a **clustergram** (clustered heatmap with row &
  column dendrograms), a **linked explorer** (heatmap ↔ network, synchronised),
  and a **2D embedding map** (PCA / t-SNE) of domain co-occurrence, in the browser.

By A. Michailidis, V. S. Papagrigoriou & C. A. Ouzounis — BCCB Group, Aristotle
University of Thessaloniki. See the in-app **How to use** and **FAQ** pages.

## Documentation
- [`docs/INDEX.md`](docs/INDEX.md) — file-by-file map of the codebase.
- [`docs/CODE_ANALYSIS.md`](docs/CODE_ANALYSIS.md) — architecture, data flow, methods, limitations.
- [`docs/METHODS.md`](docs/METHODS.md) — scientific rationale and how to interpret results.
- [`docs/DATA.md`](docs/DATA.md) — exact input/output formats.
- [`docs/API.md`](docs/API.md) — HTTP endpoint request/response schemas.
- [`docs/CLAUDE.md`](docs/CLAUDE.md) — onboarding notes for AI agents working in this repo.
- [`docs/DESIGN.md`](docs/DESIGN.md) — design system & component templates (live gallery at `/styleguide`).

These describe what the code does now, so you don't have to re-read it all.

## Tools (web)

| Page | Route | What it does |
|------|-------|--------------|
| BLAST Analysis | `/blast` | Upload a BLAST file → build correlation or feature matrix (downloadable) |
| Heatmap | `/heatmap` | Upload a matrix → heatmaps with a metric selector (feature matrices), compare-two, normalize/log, cell inspector, PNG |
| Clustergram | `/clustergram` | Hierarchically-clustered heatmap with row & column dendrograms (SciPy backend) |
| Linked explorer | `/explorer` | Clustered heatmap ↔ domain network, synchronised selection |
| Embedding map | `/embedding` | 2D PCA / t-SNE projection of profiles, KMeans groups, searchable |
| All vs All | `/all-vs-all` | Upload a correlation matrix → MCL clusters: interactive network coloured by cluster |
| Tree builder | `/tree-builder` | Upload a correlation matrix → NJ (or UPGMA) tree, async job + polling |
| Tree viewer | `/tree-viewer` | Upload a `.nw` file → collapsible radial tree (genus colours, search) |
| How to use | `/how-to` | Per-tool walkthrough |
| FAQ | `/faq` | Concepts, methods, troubleshooting, credits |

Every JSON endpoint lives under **`/api`**; everything else is a client-side
route served by the SPA. See [`docs/API.md`](docs/API.md).

Each tool page opens with a **how to read this tool** panel — the input format
with a real excerpt, plus the judgements that decide whether the output means
anything — and every drop zone offers **load an example file**, so any tool can
be tried before you have data of your own.

## Frontend

A single **Vite + React** SPA in [`frontend/`](frontend/), served by Flask at `/`
once built (the Docker image builds it). Fonts and icons are bundled, so the app
makes **no third-party requests** and works offline.

- Dev: **`./dev.sh`** starts both (Flask :8000 + Vite :5173, `/api` proxied) — or
  run them separately (`python app.py` and `cd frontend && npm install && npm run dev`).
- Build: `npm run build --prefix frontend` → `frontend/dist/`.
- Tests: `npm run test --prefix frontend`.
- Design system: [`docs/DESIGN.md`](docs/DESIGN.md) (live gallery at `/styleguide`).

The server-rendered Jinja pages that used to duplicate every tool were removed:
they had drifted (three tools existed only in React) and maintaining two clients
for the same API was the largest source of duplication in the repo.

## Quick start

### Docker (recommended)
```bash
docker compose up --build
# open http://localhost:8000
```
Uploaded/generated files persist in `./uploads`, `./downloads`, `./cache`.

### Local (Python 3.13)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py                 # dev server on http://127.0.0.1:8000
# production:
gunicorn --workers 4 --threads 4 --timeout 60 --bind 0.0.0.0:8000 app:app
```

> **macOS note:** the default port is **8000**, not 5000 — on macOS the AirPlay
> Receiver (System Settings → General → AirDrop & Handoff) occupies ports 5000
> and 7000 and will silently answer with `Server: AirTunes`, making the app look
> broken. Use 8000, or disable the AirPlay Receiver.
Job state lives in SQLite (WAL) and heavy work runs in a separate process pool, so
multiple gunicorn workers are fine. See [`docs/CODE_ANALYSIS.md`](docs/CODE_ANALYSIS.md).

## CLI

```bash
python main.py <command>
```

| Command | Action |
|---------|--------|
| `--analyze` | Build `output/correlation_matrix.csv` and `output/feature_matrix.csv` from the bundled BLAST file |
| `--construct_tree [nj\|upgma]` | Build a tree from the correlation matrix → `output/species_tree_approx.nw` |
| `--display_tree [depth]` | Open an interactive circular tree (Plotly) |
| `--all_vs_all` | Domain MCL clustering + Dash app (port 8051) |
| `--validate_clusters` | Print a clustering-quality report (clusters, modularity, same-protein co-clustering) |
| `--display_cor` / `--display_cor_features` / `--display_heatmap_spxsp` | Various heatmaps |

Typical pipeline: `--analyze` → `--construct_tree` / `--validate_clusters`.

## Input data format

BLAST tabular (`-outfmt 6`, tab-separated, 12 columns): `QueryID, SubjectID,
PercentIdentity, AlignmentLength, Mismatches, GapOpens, QueryStart, QueryEnd,
SubjectStart, SubjectEnd, EValue, BitScore`.

- **Domain** = `QueryID` (e.g. `NP_001005920.3-Cupin_8__coords_52--261`; the
  protein accession is the part before the first `-`).
- **Species** = first 4 dash-segments of `SubjectID` (e.g.
  `UP000005640-00009606-Homo_sapi-22`).
- A hit counts as **present** only when `EValue <= 1e-5` (configurable via
  `EVALUE_THRESHOLD`). The cutoff is applied in one place, so the correlation
  matrix and the feature matrix always agree on what "present" means.

## Configuration (env vars)

All of these are read in [`config.py`](config.py).

| Var | Default | Meaning |
|-----|---------|---------|
| `PORT` / `HOST` | `8000` / `127.0.0.1` | Dev server bind (5000 clashes with macOS AirPlay) |
| `FLASK_DEBUG` | `0` (off) | Enable Flask debugger (never in production) |
| `LOG_LEVEL` | `INFO` | Root logging level |
| `MAX_UPLOAD_MB` | `200` | Max upload size |
| `JOB_WORKERS` | `2` | Concurrent background jobs |
| `JOB_BACKEND` | `process` | `process` (off the GIL) or `thread` (escape hatch) |
| `JOB_TTL_SECONDS` | `86400` | How long finished jobs and their results are kept |
| `EVALUE_THRESHOLD` | `1e-5` | A BLAST hit counts as present at or below this |
| `JACCARD_THRESHOLD` | `0.5` | Minimum similarity for a domain–domain edge |
| `MCL_INFLATION` | `2.0` | MCL granularity |
| `MAX_TAXA` | `5000` | Refuse NJ above this many species (use `upgma` instead) |
| `EDGE_BUDGET_PER_NODE` | `5` | Strongest edges per node returned by the all-vs-all data endpoint |
| `TREE_DISPLAY_DEPTH` | `6` | Default depth for every tree display |
| `UPLOAD_DIR` / `DOWNLOAD_DIR` / `CACHE_DIR` / `RESULT_DIR` / `DB_PATH` | under the repo | Runtime paths |
| `DASH_DEBUG` | off | Debug mode for standalone Dash apps |

## Testing

```bash
pip install pytest
pytest -q                      # 97 tests
npm run test --prefix frontend # 6 tests
```
Covers species-key extraction, the E-value cutoff, matrix building, Jaccard
distance, **equivalence of the fast Neighbour-Joining to Bio.Phylo**
(Robinson-Foulds 0), the job store, domain clustering + validation, every HTTP
endpoint including both async jobs end to end, and the SPA's CSV parser.
CI runs all of it plus a Docker build: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Performance

Measured on the bundled dataset; see [`docs/CODE_ANALYSIS.md`](docs/CODE_ANALYSIS.md) §7.
The tree build went from 119.9 s to 0.76 s with an identical topology, the
feature matrix reaches the browser as 0.87 MB of numbers instead of 25.5 MB of
CSV, and repeated clusterings and projections are served from a cache.

## Project layout

```
app.py                  Flask app: SPA mount, /api registration, errors, job pool
config.py               Paths and every tunable knob (all env-overridable)
jobs.py                 SQLite job store (state, progress, result blobs, retention)
workers.py              Background job entry points (run in a separate process)
main.py                 CLI entry point
blueprints/*.py         JSON API (blast, matrices, heatmap, allvsall, tree)
analysis/               BLAST parsing, matrices, matrix I/O, MCL + validation
tree_construction/      Distance matrix + fast NJ/UPGMA (nj.py)
visualization/          Plotly heatmaps + the CLI-only Dash explorer
frontend/               React SPA — the UI (served at / once built)
data/                   Sample inputs (species lists + BLAST file)
tests/                  pytest suite
Dockerfile, docker-compose.yml
```
