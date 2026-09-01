# Code Analysis

Technical reference for the **current** behaviour of the codebase: architecture,
data flow, the scientific methods, request/job lifecycles, and known limitations.
File map is in [`INDEX.md`](INDEX.md).

## 1. Architecture

- **Flask app** (`app.py`). Every JSON endpoint is registered under **`/api`**
  (`blueprints/blast.py`, `matrices.py`, `heatmap.py`, `allvsall.py`, `tree.py`);
  every other path serves the built React SPA. That split is deliberate: when the
  SPA was mounted at the root while endpoints sat beside it, `/clustergram` and
  `/embedding` were simultaneously a page and an endpoint. A single download
  endpoint `GET /api/downloads/<path:filename>` serves generated files via
  `send_from_directory` (path-traversal safe).
- **Configuration** (`config.py`) holds every path and tunable knob, all
  env-overridable. Paths are absolute, so behaviour does not depend on the
  working directory gunicorn was started from.
- **CLI** (`main.py`) exposes the same analysis pipeline headlessly and exits
  non-zero on failure. One argparse parser per command: inputs and outputs are
  `-i`/`-o` arguments (defaulting to the bundled dataset and `output/`), and each
  command carries its own knobs -- `--evalue`, `--metric`, `--threshold`,
  `--inflation`, `--method`/`--axis`/`-k` -- so nothing needs an environment
  variable or a code edit. Every command has a web counterpart, including
  `--embed`, which writes the same projection `POST /api/embedding` serves.
- **Analysis core** (`analysis/`) is UI-agnostic and shared by web + CLI, and
  imports no UI framework.
- Heavy work (tree building, clustering) runs in a **separate process**
  (`workers.py` via a `ProcessPoolExecutor`); the HTTP request returns
  immediately and the client polls. State lives in a SQLite job store
  (`jobs.py`), so it survives restarts and is shared across gunicorn workers.

## 2. Data model

BLAST tabular input (`-outfmt 6`, 12 columns). Two derived identifiers:
- **Species key** = first 4 dash-segments of `SubjectID`
  (`UP000005640-00009606-Homo_sapi-22`). Computed by `extract_species` — the
  single source of truth used by every matrix builder, so labels stay consistent.
- **Domain** = `QueryID`. The **protein accession** is the substring before the
  first `-` (used as internal ground truth in clustering validation).

Matrices (rows = species, cols = domains):
- **Correlation matrix** — hit counts; a hit counts only if `EValue <= 1e-5`.
- **Feature matrix** — each cell is a JSON feature vector (mean %id, mean
  alignment length, mean bitscore, num_hits, min_evalue).

Both are built from `_load_blast`, which applies the E-value cutoff **once** for
both. They used to disagree: only the correlation matrix filtered, so the same
heatmap/clustergram/embedding tools got different presence semantics depending
on which file you uploaded.

## 3. Pipelines

### 3.1 BLAST → matrices
`_load_blast` → add `Domain`/`Species` → pivot.
- Correlation: `pivot_table(aggfunc='size', fill_value=0)` after the e-value filter.
- Feature: `groupby(['Species','Domain']).agg(...)` → JSON per cell → pivot.

### 3.2 Correlation matrix → species tree (Jaccard + NJ)
`compute_distance_matrix(corr_path)`:
1. Presence/absence profile per species (`value > 0`); drop all-zero rows;
   aggregate duplicate species (logical OR).
2. `pdist(profiles, metric='jaccard')` → `squareform` → lower-triangular list.
3. `construct_tree` → `tree_construction/nj.py` → Newick.

`nj_newick` is Neighbour-Joining with each iteration expressed in numpy. It
replaced `Bio.Phylo`'s pure-Python O(n³) implementation, which took **119.9 s**
on this repo's 848-species matrix (against 0.08 s to compute the distances
themselves) and deep-copied the whole matrix first. The vectorised version takes
**0.76 s** and produces an identical topology — asserted in `tests/test_nj.py`
by comparing bipartitions against `Bio.Phylo` (Robinson-Foulds 0). `upgma_newick`
is offered as an explicit second method (O(n²), ~5 s for 8480 taxa) but assumes a
molecular clock, so it is never substituted silently. `MAX_TAXA` turns an
eventual OOM into an actionable error.

Distances are derived from **real** domain profiles (not list order). Identical
profiles → distance 0; disjoint → 1.

### 3.3 Correlation matrix → domain clusters (MCL) + validation
`cluster_domains(corr_path, threshold=0.5, inflation=2.0)`:
1. `domain_jaccard` — domain × domain Jaccard from binary profiles
   (`inter = Bᵀ·B`, `union = pres_i + pres_j − inter`).
2. `build_domain_graph` — edge when Jaccard ≥ `threshold`, weight = Jaccard.
3. MCL (`markov_clustering.run_mcl` on the weighted sparse adjacency) →
   `get_clusters`.
4. Cluster labels straight from MCL (the co-cluster matrix and `spring_layout`
   are computed once into the cached result but are not sent unless a client
   asks for them with `?include=`).
5. `validate_clusters` report (see §5).
6. The whole payload is content-addressed cached under `cache/`, keyed on the
   file's bytes plus the parameters plus an algorithm version.

This clusters **domains by shared phylogenetic profile** (the intended goal), not
the raw bipartite species–domain graph.

### 3.4 Newick → interactive tree (viewer)
`POST /api/newick`: `Bio.Phylo.read` → `convert_tree_to_d3` (iterative,
stack-based; safe for very deep trees) → D3 JSON. Server sends the full tree;
the client depth slider prunes the view.

## 4. Web endpoints & job lifecycle

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/<anything not /api>` | `app.py` | the React bundle (index.html fallback) |
| GET | `/api/health` | `app.py` | liveness + queue info |
| GET | `/api/downloads/<path:filename>` | `app.py` | shared, traversal-safe |
| POST | `/api/upload` | blast | one validator: secure_filename + per-kind allowlist |
| POST | `/api/process` | blast | builds a matrix into `downloads/`, unique name |
| GET | `/api/results` | blast | existence check |
| POST | `/api/matrices` | matrices | store once, return `file_id` + labels |
| POST | `/api/clustergram` | heatmap | `file_id` (preferred) or inline `z` |
| POST | `/api/embedding` | heatmap | `file_id` (preferred) or inline `z` |
| POST | `/api/allvsall` | allvsall | starts a clustering job → `job_id` |
| GET | `/api/allvsall/<job_id>/status` | allvsall | poll `state` |
| GET | `/api/allvsall/<job_id>/data` | allvsall | `?include=matrix,positions` for the O(n²) extras |
| POST | `/api/trees` | tree | starts a build (`method=nj\|upgma`) → `job_id` (202) |
| GET | `/api/trees/<job_id>` | tree | `state` + legacy `status`, 404 if unknown |
| POST | `/api/newick` | tree | parses an uploaded tree for the viewer |

**Job lifecycle (both kinds are now identical).** POST saves the upload under a
uuid-prefixed name, inserts a row in the SQLite job store, submits
`workers.run_*_job` to the process pool and returns the `job_id`. The worker
reports progress at real pipeline boundaries by writing to the same store, then
records `done` (with a result: a download filename, or a gzipped JSON blob under
`results/`) or `failed`. The client polls and branches on `state`. A reaper
expires finished jobs after `JOB_TTL_SECONDS`, deleting their blobs, and fails
jobs whose worker vanished.

This replaced two incompatible in-memory models — a uuid-keyed dict for trees and
a filename-keyed pair of dicts plus a `"Completed."` magic string for all-vs-all —
which grew without bound, were lost on restart, forced a single gunicorn worker,
and let one user read another's results.

## 5. Clustering validation

MCL is unsupervised — there is no training/test split. Quality is reported by
`validate_clusters`:
- **cluster count / sizes** and number of non-trivial clusters,
- **modularity Q** of the partition on the weighted similarity graph,
- **same-protein co-clustering rate** — internal ground truth: domains sharing a
  protein accession are physically linked and *should* co-cluster,
- a **warning** when the partition collapses to one dominant cluster
  (`largest ≥ 80%` of nodes, or `Q < 0.05`).

Run via `python main.py --validate_clusters`.

## 6. Known limitations / caveats

- **Bundled dataset has weak structure.** On `Sequences-218-annot.Query.blastp`,
  domain profiles are near-uniform (median Jaccard ≈ 0.59), so MCL yields one
  dominant cluster with `Q ≈ 0` even with the e-value cutoff and correct method —
  this is the *data*, and `validate_clusters` flags it. Sharper presence calls
  (stricter `evalue_threshold`/bitscore) or richer data are needed for modules.
- **NJ is still O(n³)**, just with a ~158× smaller constant: 848 species take
  0.76 s, but 8000+ would take minutes and several GB. `MAX_TAXA` (default 5000)
  refuses those with a message pointing at `upgma`.
- **Matrices are uploaded twice in the Clustergram/Embedding flow** — once read
  locally to draw, once posted to `/api/matrices`. Cheap, but not free.
- **Heatmap tool is client-side.** It parses the uploaded CSV in the browser and
  needs no server call at all. Clustergram and Embedding parse locally *for
  rendering* but upload the file once to `/api/matrices` and reference it by id,
  so the values never travel inside a request body.
- **Security posture.** Uploads go through one validator (`secure_filename` +
  per-kind extension allowlist + `MAX_CONTENT_LENGTH`), are stored under
  unguessable uuid-prefixed names, and downloads use `send_from_directory`. Job
  ids are unguessable capability tokens — that is *not* authentication, and there
  is still no auth or per-user accounting.
- **No authentication.** Job and matrix ids are unguessable capability tokens,
  which stops accidental cross-user access but is not auth. A deployment on an
  open network needs a real access control layer in front.
- **The bundled dataset still has weak structure** (see the first bullet); that is
  the data, not the code.

## 7. Performance

Every figure below was measured on the bundled dataset (848 species x 216
domains; the feature matrix is 25.5 MB) and is regression-tested where the
optimisation could change a result.

| Step | Before | After | How |
|------|--------|-------|-----|
| Neighbour-Joining tree | 119.9 s | **0.76 s** | `nj_newick` vectorises each iteration with numpy instead of Bio.Phylo's pure-Python O(n^3) loop. Identical topology (Robinson-Foulds 0). |
| Feature matrix build | 1.02 s | **0.41 s** | `_feature_vectors` formats from zipped numpy arrays; `DataFrame.apply(axis=1)` was building a Series per row. Byte-identical output. |
| Feature matrix read (1 metric) | 0.19 s parse | **0.09 s** | Vectorised regex extraction, with the `json.loads` reference as a fallback the moment a cell does not fit. |
| Feature matrix to the browser | 25.5 MB CSV, parsed cell by cell in JS | **0.87 MB** gzipped (all metrics), **0.06 MB** (one) | `GET /api/matrices/<id>/plane` returns numbers; pandas parses the file once, server-side. |
| all-vs-all payload | 2.18 MB | **6 KB** gzipped | Strongest edges only, no stored co-cluster matrix, no spring layout, and the compressed blob is streamed verbatim. |
| Repeat clustergram / embedding | full recompute | **~0 s** | Content-addressed cache; both endpoints are deterministic (every estimator seeded, PCA included). |
| First job after a restart | +0.97 s | ~0 s | The process pool imports `markov_clustering` in its initialiser rather than inside the first job. |

What was measured and left alone: `domain_jaccard` (one matmul), MCL itself
(0.10 s), the clustergram's `pdist`/`linkage` (0.07 s), PCA and KMeans (0.09 s).
None of them are the bottleneck at this scale.

## 8. Retention

Nothing used to clean up: uploads, generated matrices, trees and in-memory job
results all accumulated forever, in bind-mounted volumes. `jobs.reap()` now runs
at startup and hourly, and it (a) deletes job rows older than `JOB_TTL_SECONDS`
along with their result blobs, (b) fails jobs whose worker vanished, and
(c) sweeps `uploads/` and `downloads/` for files past the same window.

## 9. Extension points

- Stricter presence calls: tune `create_correlation_matrix(evalue_threshold=...)`.
- Clustering granularity: `cluster_domains(threshold=..., inflation=...)`.
- Distance metric: `compute_distance_matrix(metric=...)` (any scipy `pdist` metric).
- Persistence/multi-worker: replace the in-memory `_jobs` dicts with a shared store.
