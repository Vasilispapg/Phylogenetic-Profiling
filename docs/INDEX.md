# Codebase Index

A navigation map so you don't have to read every file. Paths are relative to the
repo root. For architecture & data flow see [`CODE_ANALYSIS.md`](CODE_ANALYSIS.md).

## Entry points

- **`app.py`** — Flask app (`app`). Page routes `/`, `/tools`, `/tools/blast`,
  `/how-to`, `/faq`, `/styleguide`, `/health`; the built React SPA at `/app`;
  single shared download endpoint `GET /downloads/<path:filename>`
  (`send_from_directory`, traversal-safe). Owns the job process pool
  (`app.submit_job`), the reaper timer and the JSON error handlers. WSGI callable
  for gunicorn = `app:app`.
- **`config.py`** — every path and knob, all env-overridable (`EVALUE_THRESHOLD`,
  `JACCARD_THRESHOLD`, `MCL_INFLATION`, `MAX_TAXA`, `JOB_*`, directories).
  Creates the runtime directories and configures logging.
- **`jobs.py`** — SQLite/WAL job store: `create/update/get/progress/finish/fail`,
  gzipped result blobs under `results/`, and `reap()` for TTL expiry plus
  stranded-job sweeping.
- **`workers.py`** — `run_tree_job` / `run_allvsall_job`. These run in a separate
  process, so they import no Flask.
- **`main.py`** — CLI dispatcher. `COMMANDS` dict maps `--analyze`,
  `--construct_tree`, `--display_tree`, `--all_vs_all`, `--validate_clusters`,
  `--display_*` to functions. Constants: `BLAST_FILE_PATH`, `CORRELATION_MATRIX_PATH`,
  `FEATURE_MATRIX_PATH`.

## Flask blueprints (`blueprints/*.py` — these are Python, not HTML)

- **`blueprints/_api.py`** — `fail()` / `ok()` (real HTTP status codes) and
  `safe_upload_name()`, the single upload validator every endpoint goes through.
- **`blueprints/blast.py`** (`blast_bp`) — `POST /upload` (uuid-prefixed storage),
  `POST /process` (→ `create_correlation_matrix` / `create_feature_matrix`, writes
  a uuid-prefixed file to `downloads/`), `GET /results`.
- **`blueprints/heatmap.py`** (`heatmap_bp`) — `GET /tools/heatmap` (page) plus
  `POST /clustergram` (SciPy hierarchical clustering → leaf orders + dendrogram
  coords) and `POST /embedding` (scikit-learn PCA/t-SNE + KMeans → 2D coords +
  labels). Heatmap/clustergram/embedding pages parse CSVs client-side.
- **`blueprints/allvsall.py`** (`allvsall_bp`) — `GET/POST /tools/allvsall`
  (POST starts a background clustering job and returns its id),
  `GET /allvsall_status/<job_id>` (poll `state`),
  `GET /allvsall_data/<job_id>[?include=matrix,positions]`.
- **`blueprints/tree.py`** (`tree_bp`) — tree pages + endpoints. Key pieces:
  - `GET/POST /tools/tree_construct` — POST starts a background build (`method=nj|upgma`),
    returns `job_id` with 202.
  - `GET /tools/tree_status?job_id=` — `status` (legacy) plus `state`/`progress`, or 404.
  - `POST /tools/tree_viewer` — parse uploaded Newick → D3 JSON (`convert_tree_to_d3`,
    `get_max_depth`, both iterative/stack-based).

## Analysis pipeline (`analysis/`)

- **`utils.py`** — `extract_species(subject_id)`: canonical species key = first 4
  dash-segments, the single source of truth for both matrix builders.
- **`matrix_operations.py`** — core matrices:
  - `_load_blast` — read BLAST tabular, **apply the E-value cutoff**, add
    `Domain`/`Species` columns. Both builders go through it, so they agree.
  - `create_correlation_matrix` — species × domain presence/count matrix.
  - `create_feature_matrix` — species × domain JSON feature vectors.
  - `find_true_positives(corr_path)` — vectorized list of (species, domain) pairs > 0.
- **`clustering_analysis.py`** — domain-profile MCL clustering, UI-framework free:
  - `domain_jaccard(corr_df)` → (domains, Jaccard matrix).
  - `build_domain_graph(domains, J, threshold)` → weighted nx graph.
  - `cluster_labels` / `co_cluster_matrix` — the partition, and its dense form.
  - `cluster_payload(...)` → the API-shaped, content-addressed cached dict used by
    the web (O(n) on the wire).
  - `cluster_domains(...)` → the legacy `(graph, nodes, all_vs_all_df, pos, metrics)`
    tuple used by the CLI.
  - `validate_clusters(graph, clusters, nodes)` → metrics dict (n_clusters,
    modularity, same_protein_cocluster_rate, warning).

## Tree construction (`tree_construction/`)

- **`nj.py`** — `nj_newick` (Neighbour-Joining vectorised with numpy; 158× faster
  than Bio.Phylo with an identical topology, asserted in `tests/test_nj.py`),
  `upgma_newick` (explicit O(n²) alternative), `check_size` (the `MAX_TAXA` guard).
- **`construct_tree.py`** —
  - `load_profile_matrix(path)` — presence/absence profile (drops empty rows,
    aggregates duplicate species).
  - `compute_square_distances(path, metric="jaccard")` → (species, square array).
    Preferred; `compute_distance_matrix` is the lower-triangle form kept for the CLI.
  - `construct_tree(species, distances, output_path, method="nj")` → Newick.
- **`display_tree.py`** — `display_tree` / `convert_tree_to_circular_plotly`
  (interactive circular tree, CLI only).

## Visualization (`visualization/`)

- **`dash_allvsall.py`** — `create_dash_app`, the CLI-only Dash explorer. Lives
  here so no web blueprint transitively imports Dash/Plotly.
- **`display_correlation.py`** — `display_species_domain_heatmap` and
  `display_species_domain_heatmap_with_features` (Dash; JSON cells parsed with
  `json.loads`, never `eval`).
- **`display_species_correlation.py`** — `display_heatmap_speciesxspecies`
  (species × species correlation + dendrogram; NaNs filled before linkage).

## Frontend (`pages/`, `public/`)

- **`pages/tools.html`** — base layout + nav (uses blueprint-qualified `url_for`).
  All tool pages `{% extends "tools.html" %}`.
- **`pages/index.html`** — PhyloFlask landing page.
- **`pages/help.html`** — "How to use" guide (`/how-to`).
- **`pages/faq.html`** — FAQ + concepts + credits (`/faq`).
- **`pages/styleguide.html`** — living design-system gallery (`/styleguide`); see `docs/DESIGN.md`.
- **`pages/blast.html`** — drop-zone upload + process; download via `/downloads/<filename>`.
- **`pages/tree_construct.html`** — upload correlation matrix, poll by `job_id`.
- **`pages/tree_viewer.html`** — collapsible radial D3 tree (genus colours, search).
- **`pages/allvsall.html`** — Cytoscape network (cluster colours, slider, layouts)
  linked to a Plotly co-cluster heatmap.
- **`pages/heatmap.html`** — client-side heatmap tool (order/log toggles, cell-click).
- **`public/assets/css/tools.css`** — shared themed components, responsive rules, polish.
- **`public/assets/js/tools.js`** — `Phylo` helpers: dropzone, upload, poll, status
  (status text is inserted with `textContent`, never as markup).

## React SPA (`frontend/`)

Vite + React app consuming the same JSON API, served by Flask at **`/app`** once
built (the Docker image builds it). The Jinja pages are still served at `/`; which
one is canonical is an open decision. Run both dev servers with **`./dev.sh`**.

- **`src/lib/matrix.js`** — shared CSV parse (PapaParse; handles JSON feature
  cells with embedded commas), ordering, per-row/col normalize + log transforms.
- **`src/lib/api.js`** — fetch helpers; surfaces a clear error when the backend is
  unreachable instead of a cryptic `Unexpected end of JSON input`.
- **`src/pages/`** — `Landing`, `Blast`, `Heatmap` (metric selector, compare-two,
  cell inspector), **`Clustergram`** (heatmap + row/col dendrograms), **`Explorer`**
  (linked clustered heatmap ↔ domain network), **`Embedding`** (PCA/t-SNE map +
  searchable group panel), `AllVsAll` (fcose component layout), `TreeViewer`,
  `TreeBuilder`, `HowTo`, `Faq`, `StyleGuide`.
- **`src/components/Layout.jsx`** — header with a Tools mega-dropdown (hover-bridge
  so it doesn't close on cursor move) + a mobile hamburger menu.
- Extra deps: `cytoscape-fcose` (network layout), `papaparse` (CSV), `plotly.js`,
  `d3`, `cytoscape`.

## Data & outputs

- **`data/list.2`**, **`data/list.3`** — species lists (`TaxID-SpeciesCode`).
- **`data/Sequences-218-annot.Query.blastp`** — sample BLAST tabular input.
- **`output/`** — CLI outputs (gitignored). **`downloads/`** — web outputs (gitignored).
  **`uploads/`**, **`cache/`** — runtime (gitignored).

## Tests & ops

- **`tests/test_pipeline.py`** — species keys, the E-value cutoff, matrices, true
  positives, Jaccard distances, both tree methods.
- **`tests/test_nj.py`** — equivalence of the fast NJ to Bio.Phylo (Robinson-Foulds 0),
  Newick quoting, the `MAX_TAXA` guard.
- **`tests/test_jobs.py`** — job store transitions, blobs, TTL reaping, stranded jobs.
- **`tests/test_web.py`** — every endpoint including both async jobs end to end,
  status codes, path-traversal block, upload validation, upload isolation.
- **`tests/conftest.py`** — adds repo root to `sys.path` and redirects all runtime
  directories to a scratch dir.
- **`frontend/src/lib/matrix.test.js`** — the SPA's CSV parser (vitest).
- **`.github/workflows/ci.yml`** — pytest, vitest, SPA build, Docker build.
- **`Dockerfile`** (multi-stage: builds the SPA, then the app),
  **`docker-compose.yml`**, **`.dockerignore`** — containerized run.
