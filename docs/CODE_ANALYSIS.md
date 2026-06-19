# Code Analysis

Technical reference for the **current** behaviour of the codebase: architecture,
data flow, the scientific methods, request/job lifecycles, and known limitations.
File map is in [`INDEX.md`](INDEX.md).

## 1. Architecture

- **Flask app** (`app.py`) with four **blueprints** (`templates/blast.py`,
  `heatmap.py`, `allvsall.py`, `tree.py`). Templates live in `pages/`, static in
  `public/`. A single download endpoint `GET /downloads/<path:filename>` serves
  generated files via `send_from_directory` (path-traversal safe).
- **CLI** (`main.py`) exposes the same analysis pipeline headlessly.
- **Analysis core** (`analysis/`) is UI-agnostic and shared by web + CLI.
- Heavy work (tree building, clustering) runs in **background threads**; the HTTP
  request returns immediately and the client polls for status.

## 2. Data model

BLAST tabular input (`-outfmt 6`, 12 columns). Two derived identifiers:
- **Species key** = first 4 dash-segments of `SubjectID`
  (`UP000005640-00009606-Homo_sapi-22`). Computed by `extract_species` — the
  single source of truth used by every matrix builder, so labels stay consistent.
- **Domain** = `QueryID`. The **protein accession** is the substring before the
  first `-` (used as internal ground truth in clustering validation).

Matrices (rows = species, cols = domains):
- **Correlation matrix** — hit counts; a hit counts only if `EValue <= 1e-5`
  (`create_correlation_matrix`, `evalue_threshold`).
- **Feature matrix** — each cell is a JSON feature vector (mean %id, mean
  alignment length, mean bitscore, num_hits, min_evalue).

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
3. `construct_tree` → Bio.Phylo `DistanceTreeConstructor().nj()` → Newick.

Distances are derived from **real** domain profiles (not list order). Identical
profiles → distance 0; disjoint → 1.

### 3.3 Correlation matrix → domain clusters (MCL) + validation
`cluster_domains(corr_path, threshold=0.5, inflation=2.0)`:
1. `domain_jaccard` — domain × domain Jaccard from binary profiles
   (`inter = Bᵀ·B`, `union = pres_i + pres_j − inter`).
2. `build_domain_graph` — edge when Jaccard ≥ `threshold`, weight = Jaccard.
3. MCL (`markov_clustering.run_mcl` on the weighted sparse adjacency) →
   `get_clusters`.
4. Domain × domain **co-cluster** ("all-vs-all") matrix + `spring_layout` positions.
5. `validate_clusters` report (see §5).

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

**Job lifecycle (tree construct):** POST saves upload as
`uploads/{job_id}_{name}`, sets `_jobs[job_id]={status:"in_progress",...}` **before**
starting the thread, returns `job_id`. The worker thread runs `compute_distance_matrix`
+ `construct_tree`, then sets `completed` (with `result` path) or `failed` (with
`error`). The client polls `/tools/tree_status?job_id=` and stops on
`completed`/`failed`/404. **allvsall** is analogous but keyed by the (secured)
filename. All shared dicts are guarded by a `Lock`.

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
- **NJ is O(n³).** ~600 species ≈ 1 min; the full ~3000-species set would take
  hours. `construct_tree` raises the recursion limit and prints a warning.
- **In-memory job state.** `_jobs`/`precomputed_results` live in process memory →
  run gunicorn with **1 worker** (threads for concurrency). State is lost on
  restart. A persistent store (Redis/SQLite) would be needed for multi-worker.
- **Clustering not cached.** Domain clustering is cheap (216 domains), so the old
  pickle cache was removed. (Tree NJ is the expensive step.)
- **Heatmap tool is client-side.** No server data endpoint; it parses uploaded
  CSVs in the browser.
- **Security posture.** Uploads use `secure_filename` + extension allowlist +
  `MAX_CONTENT_LENGTH`; downloads use `send_from_directory`; Flask debug is off
  unless `FLASK_DEBUG=1`. Still single-tenant; no auth.
- **Legacy/dead links.** `index.html` has placeholder `/features` and `/contact`
  links with no backing routes.

## 7. Extension points

- Stricter presence calls: tune `create_correlation_matrix(evalue_threshold=...)`.
- Clustering granularity: `cluster_domains(threshold=..., inflation=...)`.
- Distance metric: `compute_distance_matrix(metric=...)` (any scipy `pdist` metric).
- Persistence/multi-worker: replace the in-memory `_jobs` dicts with a shared store.
