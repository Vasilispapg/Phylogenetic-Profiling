# Code Analysis

Technical reference for the **current** behaviour of the codebase: architecture,
data flow, the scientific methods, request/job lifecycles, and known limitations.
File map is in [`INDEX.md`](INDEX.md).

## 1. Architecture

- **Flask app** (`app.py`) with four **blueprints** (`blueprints/blast.py`,
  `heatmap.py`, `allvsall.py`, `tree.py` — Python, not Jinja; the templates live
  in `pages/`, static in `public/`). A single download endpoint
  `GET /downloads/<path:filename>` serves generated files via
  `send_from_directory` (path-traversal safe). The built React SPA is mounted at
  `/app`.
- **Configuration** (`config.py`) holds every path and tunable knob, all
  env-overridable. Paths are absolute, so behaviour does not depend on the
  working directory gunicorn was started from.
- **CLI** (`main.py`) exposes the same analysis pipeline headlessly and exits
  non-zero on failure.
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
`POST /tools/tree_viewer`: `Bio.Phylo.read` → `convert_tree_to_d3` (iterative,
stack-based; safe for very deep trees) → D3 JSON. Server sends the full tree;
the client depth slider prunes the view.

## 4. Web endpoints & job lifecycle

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/`, `/tools`, `/tools/blast`, `/how-to`, `/faq` | `app.py` | pages |
| GET | `/downloads/<path:filename>` | `app.py` | shared, traversal-safe |
| POST | `/upload` | blast | secure_filename + extension allowlist |
| POST | `/process` | blast | builds matrix → `downloads/`, returns `filename` |
| GET | `/results` | blast | existence check |
| GET | `/tools/heatmap` | heatmap | client-side only |
| GET/POST | `/tools/allvsall` | allvsall | POST starts clustering job |
| GET | `/allvsall_status/<f>`, `/allvsall_data/<f>` | allvsall | poll + fetch (data includes node_cluster, degree, edge weights, metrics) |
| GET/POST | `/tools/tree_construct` | tree | POST → `job_id` (202) |
| GET | `/tools/tree_status?job_id=` | tree | `in_progress\|completed\|failed`, 404 if unknown |
| GET/POST | `/tools/tree_viewer` | tree | POST parses Newick |

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
- **`/clustergram` and `/embedding` take the matrix in the request body.** That is
  fine at the current scale but is O(cells) on the wire; `MAX_CELLS` caps it at
  20M with a 413. Referencing an uploaded file by id would remove the round trip.
- **Heatmap tool is client-side.** No server data endpoint; it parses uploaded
  CSVs in the browser.
- **Security posture.** Uploads go through one validator (`secure_filename` +
  per-kind extension allowlist + `MAX_CONTENT_LENGTH`), are stored under
  unguessable uuid-prefixed names, and downloads use `send_from_directory`. Job
  ids are unguessable capability tokens — that is *not* authentication, and there
  is still no auth or per-user accounting.
- **Two front-ends.** Both the Jinja pages and the React SPA are served and must
  be kept in step; which one is canonical has not been decided.
- **The bundled dataset still has weak structure** (see the first bullet); that is
  the data, not the code.

## 7. Extension points

- Stricter presence calls: tune `create_correlation_matrix(evalue_threshold=...)`.
- Clustering granularity: `cluster_domains(threshold=..., inflation=...)`.
- Distance metric: `compute_distance_matrix(metric=...)` (any scipy `pdist` metric).
- Persistence/multi-worker: replace the in-memory `_jobs` dicts with a shared store.
