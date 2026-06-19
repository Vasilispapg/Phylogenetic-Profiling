# Codebase Index

A navigation map so you don't have to read every file. Paths are relative to the
repo root. For architecture & data flow see [`CODE_ANALYSIS.md`](CODE_ANALYSIS.md).

## Entry points

- **`app.py`** — Flask app (`app`). Page routes `/`, `/tools`, `/tools/blast`;
  single shared download endpoint `GET /downloads/<path:filename>`
  (`send_from_directory`, traversal-safe). Registers all blueprints. Reads
  `PORT/HOST/FLASK_DEBUG/MAX_UPLOAD_MB` from env. WSGI callable for gunicorn = `app:app`.
- **`main.py`** — CLI dispatcher. `COMMANDS` dict maps `--analyze`,
  `--construct_tree`, `--display_tree`, `--all_vs_all`, `--validate_clusters`,
  `--display_*` to functions. Constants: `BLAST_FILE_PATH`, `CORRELATION_MATRIX_PATH`,
  `FEATURE_MATRIX_PATH`.

## Flask blueprints (`templates/*.py` — these are Python, not HTML)

- **`templates/blast.py`** (`blast_bp`) — `POST /upload` (secure_filename +
  extension allowlist), `POST /process` (→ `create_correlation_matrix` /
  `create_feature_matrix`, writes to `downloads/`), `GET /results`.
- **`templates/heatmap.py`** (`heatmap_bp`) — `GET /tools/heatmap` only; the page
  does all CSV parsing/plotting client-side (no data endpoint needed).
- **`templates/allvsall.py`** (`allvsall_bp`) — `GET/POST /tools/allvsall`
  (POST starts a background `cluster_domains` job), `GET /allvsall_status/<f>`,
  `GET /allvsall_data/<f>`. Shared `precomputed_results`/`progress_status` dicts
  guarded by one `Lock`.
- **`templates/tree.py`** (`tree_bp`) — tree pages + endpoints. Key pieces:
  - `GET/POST /tools/tree_construct` — POST starts a background NJ build, returns `job_id`.
  - `GET /tools/tree_status?job_id=` — job status (`in_progress|completed|failed`, or 404).
  - `POST /tools/tree_viewer` — parse uploaded Newick → D3 JSON (`convert_tree_to_d3`,
    `get_max_depth`, both iterative/stack-based).
  - `_jobs` dict + `_jobs_lock`; jobs keyed by uuid `job_id`.

## Analysis pipeline (`analysis/`)

- **`utils.py`** — `extract_species(subject_id)` (canonical species key = first 4
  dash-segments; the single source of truth) and `extract_partial_species`.
- **`matrix_operations.py`** — core matrices:
  - `_load_blast` — read BLAST tabular, add `Domain`/`Species` columns.
  - `create_correlation_matrix(...evalue_threshold=1e-5)` — species × domain
    presence/count matrix (presence requires `EValue <= threshold`).
  - `create_feature_matrix` — species × domain JSON feature vectors.
  - `find_true_positives(corr_path)` — vectorized list of (species, domain) pairs > 0.
- **`clustering_analysis.py`** — domain-profile MCL clustering:
  - `domain_jaccard(corr_df)` → (domains, Jaccard matrix).
  - `build_domain_graph(domains, J, threshold)` → weighted nx graph.
  - `cluster_domains(corr_path, threshold=0.5, inflation=2.0, run_dash=False)` →
    `(graph, nodes, all_vs_all_df, pos)`; prints validation.
  - `validate_clusters(graph, clusters, nodes)` → metrics dict (n_clusters,
    modularity, same_protein_cocluster_rate, warning).
  - `create_dash_app` / `create_dash_component` — Dash UI for the graph + heatmap.
- **`blast_processing.py`** — `load_blast_data` (lightweight loader; uses
  `extract_species`). Currently not on the main paths.

## Tree construction (`tree_construction/`)

- **`construct_tree.py`** —
  - `load_profile_matrix(path)` — presence/absence profile (drops empty rows,
    aggregates duplicate species).
  - `compute_distance_matrix(path, metric="jaccard")` → (species, lower-triangle).
  - `construct_tree(species, lower_triangle, output_path)` — Bio.Phylo NJ → Newick.
  - `load_species_data` — parse a bare `TaxID-SpeciesCode` list (legacy helper).
- **`display_tree.py`** — `display_tree` / `convert_tree_to_circular_plotly`
  (interactive circular tree, CLI only).

## Visualization (`visualization/`)

- **`display_correlation.py`** — `display_species_domain_heatmap` and
  `display_species_domain_heatmap_with_features` (Dash; JSON cells parsed with
  `json.loads`, never `eval`).
- **`display_species_correlation.py`** — `display_heatmap_speciesxspecies`
  (species × species correlation + dendrogram; NaNs filled before linkage).

## Frontend (`pages/`, `public/`)

- **`pages/tools.html`** — base layout + nav (uses blueprint-qualified `url_for`).
  All tool pages `{% extends "tools.html" %}`.
- **`pages/index.html`** — landing page.
- **`pages/blast.html`** — upload + process; download via `/downloads/<filename>`.
- **`pages/tree_construct.html`** — upload correlation matrix, poll by `job_id`.
- **`pages/tree_viewer.html`** — D3 radial tree; depth slider prunes client-side.
- **`pages/allvsall.html`** — Cytoscape graph + heatmap of clustering results.
- **`pages/heatmap.html`** — self-contained client-side heatmap tool.
- **`public/main.js`** — null-safe fallback upload handlers (no-op where forms absent).

## Data & outputs

- **`data/list.2`**, **`data/list.3`** — species lists (`TaxID-SpeciesCode`).
- **`data/Sequences-218-annot.Query.blastp`** — sample BLAST tabular input.
- **`output/`** — CLI outputs (gitignored). **`downloads/`** — web outputs (gitignored).
  **`uploads/`**, **`cache/`** — runtime (gitignored).

## Tests & ops

- **`tests/test_pipeline.py`** — species keys, matrices, true positives, Jaccard
  tree, domain clustering + validation.
- **`tests/test_web.py`** — route smoke tests, 404s, path-traversal block, upload validation.
- **`tests/conftest.py`** — adds repo root to `sys.path`.
- **`Dockerfile`**, **`docker-compose.yml`**, **`.dockerignore`** — containerized run.
