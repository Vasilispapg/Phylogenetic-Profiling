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
- [`docs/DEPLOY.md`](docs/DEPLOY.md) — production deploy: secrets, nginx, rate limits, rollback.
- [`docs/DESIGN.md`](docs/DESIGN.md) — design system & component templates (live gallery at `/styleguide`).

These describe what the code does now, so you don't have to re-read it all.

## Tools (web)

| Page | Route | What it does |
|------|-------|--------------|
| BLAST Analysis | `/blast` | Upload a BLAST file → build correlation or feature matrix (downloadable) |
| Heatmap | `/heatmap` | Upload a matrix → heatmaps with a metric selector (feature matrices), compare-two, normalize/log, cell inspector, PNG |
| Clustergram | `/clustergram` | Hierarchically-clustered heatmap with row & column dendrograms (SciPy backend) |
| Linked explorer | `/explorer` | Clustered heatmap ↔ domain network, synchronised selection |
| Embedding map | `/embedding` | 2D PCA / t-SNE projection of profiles, KMeans groups, searchable (draws without WebGL where the browser has none) |
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

## Safety on an open instance

The deployed instance takes uploads from anyone, so the app defends itself
instead of assuming there is a proxy in front of it:

- **Uploads are validated as they stream to disk**
  ([`analysis/upload_guard.py`](analysis/upload_guard.py)): a per-kind size
  ceiling (64 MB for BLAST and matrices, 8 MB for Newick), a maximum line
  length, a Newick nesting limit, and a **content sniff** — the first lines have
  to look like the format the extension claims. A bad file never lands whole and
  is never read into memory to be judged.
- **Two rate-limit budgets** ([`guard.py`](guard.py)), because submitting work is
  rare and expensive while polling a running job is frequent and cheap. A client
  that keeps overrunning the expensive budget collects strikes, and enough
  strikes earn a temporary ban that doubles each time. The counters live in the
  jobs database, so the limits hold across gunicorn workers rather than being
  four times looser than they look.
- **A strict Content-Security-Policy** plus `nosniff`, `no-referrer` and
  `DENY` framing. Fonts, icons and scripts are all bundled and the app loads
  nothing from anywhere else, which makes `default-src 'self'` honest rather
  than aspirational.
- Uploaded content is **data, never instructions**: it only ever reaches pandas,
  NumPy, SciPy and Bio.Phylo as something to parse.
  [`tests/test_no_execution.py`](tests/test_no_execution.py) fails if `eval`,
  `exec`, `pickle`, `subprocess` or a shell ever appears in the server code.

## Deploying

Production runs behind nginx on a single VPS. Pushing to `main` builds the image,
publishes it to GHCR and restarts the container over SSH — see
[`docs/DEPLOY.md`](docs/DEPLOY.md) for the secrets to set, the nginx config
(including the rate limits that keep an open instance sane) and how to roll back.

The server runs [`docker-compose.prod.yml`](docker-compose.prod.yml), which pulls
the published image rather than building: a smaller `MAX_UPLOAD_MB` (32 — the
bundled 218-query BLAST file is 14 MB), `TRUSTED_PROXY=1` so the rate limiter
sees the visitor instead of nginx, a health check, and `BIND` for the address to
listen on — never `0.0.0.0`, since nginx should be the only way in.

## Quick start

### Docker (recommended)
```bash
docker compose up --build
# open http://localhost:8000
```
Uploaded and generated files persist in `./uploads`, `./downloads`, `./cache`;
the job database and result blobs in `./state`.

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
python main.py <command> [-i INPUT] [-o OUTPUT]
python main.py <command> --help          # the options for one command
```

Paths are arguments, not constants: every command takes `-i/--input`, and the
ones that write a file take `-o/--output`. The defaults are the bundled dataset
and `output/`, so the bare commands below still do what they always did, and
they are absolute — a command behaves the same from any working directory.

| Command | Action | Its own options |
|---------|--------|-----------------|
| `--analyze` | Build `correlation_matrix.csv` and `feature_matrix.csv` (default: the bundled BLAST file → `output/`) | `--evalue E\|none`, `--using-pi` |
| `--construct_tree [nj\|upgma]` | Build a tree from a correlation matrix (default → `output/species_tree_approx.nw`) | `--metric jaccard\|dice\|hamming\|…` |
| `--embed` | Project profiles into 2D and write the coordinates as JSON | `--method pca\|tsne`, `--axis domains\|species`, `-k N`, `--feature NAME`, `--show` |
| `--all_vs_all` | Domain MCL clustering + Dash app (port 8051) | `--threshold J`, `--inflation I` |
| `--validate_clusters` | Print a clustering-quality report (clusters, modularity, same-protein co-clustering) | `--threshold J`, `--inflation I` |
| `--display_tree [depth]` | Open an interactive circular tree (Plotly) | |
| `--display_cor` / `--display_cor_features` / `--display_heatmap_spxsp` | Various heatmaps | |

The knobs that used to be environment-variable-only are flags now, so a sweep is
a loop rather than an `export`: `--evalue`, `--metric`, `--threshold`,
`--inflation`. Each still defaults to what [`config.py`](config.py) says.

A run on your own data, start to finish:

```bash
python main.py --analyze -i data/mine.blastp -o runs/mine --evalue 1e-10
python main.py --construct_tree -i runs/mine/correlation_matrix.csv -o runs/mine/tree.nw
python main.py --validate_clusters -i runs/mine/correlation_matrix.csv --inflation 2.5
python main.py --embed -i runs/mine/correlation_matrix.csv -o runs/mine/embedding.json \
               --method tsne --show
```

`--embed` writes `{names, coords, labels, n_clusters, method, axis, k}` — the
same projection the Embedding map serves, as JSON you can script against;
`--show` opens the Plotly scatter as well.

The CLI and the web API call the same functions on the same inputs, so their
outputs are byte-identical; the web wraps them in uploads, a job store and a
worker process, and the CLI runs them inline.

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

Read in [`config.py`](config.py), except where a row says otherwise.

| Var | Default | Meaning |
|-----|---------|---------|
| `PORT` / `HOST` | `8000` / `127.0.0.1` | Dev server bind (5000 clashes with macOS AirPlay) |
| `FLASK_DEBUG` | `0` (off) | Enable Flask debugger (never in production) |
| `LOG_LEVEL` | `INFO` | Root logging level |
| `MAX_UPLOAD_MB` | `200` | Max upload size |
| `JOB_WORKERS` | `2` | Concurrent background jobs |
| `JOB_BACKEND` | `process` | `process` (off the GIL) or `thread` (escape hatch) |
| `JOB_TTL_SECONDS` | `86400` | How long finished jobs and their results are kept |
| `REAP_INTERVAL_SECONDS` | `3600` | How often expired jobs, blobs and client counters are swept |
| `EVALUE_THRESHOLD` | `1e-5` | A BLAST hit counts as present at or below this (CLI: `--evalue`) |
| `SPECIES_SEGMENTS` | `4` | Leading dash-segments of a `SubjectID` that name a species |
| `JACCARD_THRESHOLD` | `0.5` | Minimum similarity for a domain–domain edge (CLI: `--threshold`) |
| `MCL_INFLATION` | `2.0` | MCL granularity (CLI: `--inflation`) |
| `MAX_TAXA` | `5000` | Refuse NJ above this many species (use `upgma` instead) |
| `EDGE_BUDGET_PER_NODE` | `5` | Strongest edges per node returned by the all-vs-all data endpoint |
| `TREE_DISPLAY_DEPTH` | `6` | Default depth for every tree display |
| `TREE_DISPLAY_MAX_DEPTH` | `30` | Deepest a client may ask for |
| `RATE_LIMIT_ENABLED` | `1` (on) | In-app rate limiting (nginx also limits at the edge) |
| `RATE_HEAVY_PER_MIN` | `20` | Uploads and job submissions per client per minute |
| `RATE_API_PER_MIN` | `240` | Polling and result reads per client per minute |
| `BAN_AFTER_STRIKES` | `5` | Overruns of the heavy budget before a ban |
| `BAN_SECONDS` / `BAN_SECONDS_MAX` | `900` / `86400` | First ban length; it doubles up to the cap |
| `TRUSTED_PROXY` | `0` (off) | Believe `X-Forwarded-For` — only true behind nginx |
| `UPLOAD_DIR` / `DOWNLOAD_DIR` / `CACHE_DIR` / `RESULT_DIR` / `OUTPUT_DIR` / `DB_PATH` | under the repo | Runtime paths |
| `DASH_DEBUG` | off | Debug mode for the CLI-only Dash app (read in `visualization/dash_allvsall.py`) |

## Testing

```bash
pip install pytest
pytest -q                      # 163 tests
npm run test --prefix frontend # 12 tests
```
Covers species-key extraction, the E-value cutoff, matrix building, Jaccard
distance, **equivalence of the fast Neighbour-Joining to Bio.Phylo**
(Robinson-Foulds 0), the job store, domain clustering + validation, every HTTP
endpoint including both async jobs end to end, upload validation and sniffing,
the rate limiter and its bans, the "uploads are never executed" check over all
server code, and the SPA's CSV parser and theme.
CI runs all of it plus a Docker build: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Performance

Measured on the bundled dataset; see [`docs/CODE_ANALYSIS.md`](docs/CODE_ANALYSIS.md) §7.
The tree build went from 119.9 s to 0.76 s with an identical topology, the
feature matrix reaches the browser as 0.87 MB of numbers instead of 25.5 MB of
CSV, and repeated clusterings and projections are served from a cache.

## Project layout

```
app.py                Flask app: SPA mount, /api registration, limits, job pool
config.py             Paths and every tunable knob (all env-overridable)
jobs.py               SQLite job store (state, progress, result blobs, retention)
guard.py              Per-client rate limiting and banning (same database)
workers.py            Background job entry points (run in a separate process)
main.py               CLI entry point
dev.sh                Start the Flask API and the Vite dev server together
requirements.txt      Python deps (the SPA's are in frontend/package.json)
blueprints/           JSON API — _api, blast, matrices, heatmap, allvsall, tree
analysis/             BLAST parsing, matrices, matrix I/O, MCL, embedding, upload_guard
tree_construction/    construct_tree, nj.py (fast NJ/UPGMA), display_tree (CLI)
visualization/        Plotly heatmaps and embedding plot + the CLI-only Dash explorer
frontend/             React SPA — src/{pages,components,lib}, built to dist/
data/                 Sample inputs: two species lists + the BLAST file
docs/                 The documents listed at the top
tests/                pytest suite (conftest redirects every runtime path)
uploads/ downloads/   Runtime, gitignored: what came in, what was generated
cache/ output/        Runtime, gitignored: memoised results, CLI outputs
jobs.sqlite results/  Runtime, gitignored: job store and gzipped result blobs
state/                Where those two live in Docker (mounted; see compose)
Dockerfile            Multi-stage: builds the SPA, then the app
docker-compose.yml    Local run; docker-compose.prod.yml is the deployed one
.github/workflows/    ci.yml — pytest, vitest, SPA build, Docker build
.github/ISSUE_TEMPLATE/  Issue forms; PULL_REQUEST_TEMPLATE.md sits beside them
FIXES.md              The audit fixes: where each lands, cost, payoff (Greek)
```

## Licence, citation and contributing

**MIT Licence** — see [`LICENSE`](LICENSE). Copyright is held by the Aristotle
University of Thessaloniki, where the work was done.

If PhyloFlask supports a publication, cite it with [`CITATION.cff`](CITATION.cff)
("Cite this repository" in the GitHub sidebar generates BibTeX and APA).

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — setup, the tests CI insists on, and the
  rules that are enforced rather than suggested (no execution of uploaded
  content, no third-party requests from the browser, one species key, one
  presence rule).
- [`SECURITY.md`](SECURITY.md) — report a vulnerability privately, never in an
  issue; what is in and out of scope for an instance that takes public uploads.
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — Contributor Covenant 2.1.
