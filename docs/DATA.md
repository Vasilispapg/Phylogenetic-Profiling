# Data Formats

Exact shapes of every input and output the app reads or writes.

## Inputs

### BLAST tabular (`data/*.blastp`)
Standard BLAST `-outfmt 6`: tab-separated, **no header**, 12 columns:

| # | Column | Notes |
|---|--------|-------|
| 1 | QueryID | the **Domain** id (see anatomy below) |
| 2 | SubjectID | encodes the **Species** (see anatomy below) |
| 3 | PercentIdentity | |
| 4 | AlignmentLength | |
| 5 | Mismatches | |
| 6 | GapOpens | |
| 7 | QueryStart | |
| 8 | QueryEnd | |
| 9 | SubjectStart | |
| 10 | SubjectEnd | |
| 11 | EValue | presence requires `EValue <= 1e-5` |
| 12 | BitScore | |

**SubjectID anatomy** — `UP000005640-00009606-Homo_sapi-22-001536-E-013170`
- `UP000005640` proteome, `00009606` taxid, `Homo_sapi` species, `22` …
- **Species key** = first **4** dash-segments → `UP000005640-00009606-Homo_sapi-22`
  (computed by `extract_species`).

**QueryID anatomy** — `NP_001005920.3-Cupin_8__coords_52--261`
- **Protein accession** = substring before the first `-` → `NP_001005920.3`
  (used as internal ground truth in clustering validation).
- The rest is the domain name + coordinates.

### Species list (`data/list.2`, `data/list.3`)
One `TaxID-SpeciesCode` per line, e.g. `00000048-Arch_geph`. Sample data only —
nothing in the pipeline reads these; distances come from the profile matrix.

### Correlation matrix CSV (input to tree-construct & all-vs-all)
Produced by this app or supplied by the user. Rows = species, columns = domains:
```
Species,DomainA,DomainB,...
UP000000305-00006669-Daph_pule-22,0,1,...
```
First column is the species index; cells are hit **counts** (presence == > 0).

### Newick (input to tree viewer)
Standard Newick `.nw`, e.g. `(A:0.1,(B:0.2,C:0.2):0.1);`.

## Outputs

### Correlation matrix — `output/correlation_matrix.csv` (CLI) / `downloads/<uuid>_correlation_matrix.csv` (web)
Same shape as the correlation-matrix input above.

### Feature matrix — `output/feature_matrix.csv` / `downloads/<uuid>_feature_matrix.csv`
Rows = species, columns = domains. Hits are filtered by the **same** `EValue <= 1e-5`
cutoff as the correlation matrix, so the two files are directly comparable (this
was not true before). Each cell is a **JSON string**:
```json
{"mean_percent_identity": 92.4, "mean_alignment_length": 1579.0,
 "mean_bitscore": 2957.0, "num_hits": 1, "min_evalue": 0.0}
```
Empty (species, domain) combinations are filled with the all-zero vector of the
same keys.

### Species tree — `output/species_tree_approx.nw` / `downloads/<uuid>_<name>.nw`
Newick; leaf names are species keys (quoted if they contain Newick punctuation);
branch lengths are NJ distances in Jaccard units.

### Embedding — `output/embedding.json` (CLI) / `POST /api/embedding` (web)
Written by `python main.py --embed`. One point per domain (or species), in the
order of `names`:
```json
{"axis": "domains", "method": "pca", "k": 8,
 "names": ["NP_001005920.3-Cupin_8__coords_52--261", "..."],
 "coords": [[0.59, -1.73], "..."], "labels": [5, "..."], "n_clusters": 8}
```
`labels` is the KMeans grouping used for colour. The web endpoint returns the
same `coords`/`labels`/`n_clusters` without `names`, since the client already
holds the matrix. A `note` field appears when t-SNE ran on too few points to mean
anything.

### All-vs-all (web JSON, not a file)
`GET /api/allvsall/<job_id>/data` returns domain nodes with their cluster id and
degree, the strongest Jaccard-weighted edges (plus `edges_total`), and a
validation `metrics` object. The co-cluster matrix and 2-D positions are
`?include=`-only. See [`API.md`](API.md).

## Where files live
- `output/` — CLI outputs (matrices, tree, `embedding.json`). `downloads/` — web
  outputs. `uploads/` — uploads.
  `cache/` — content-addressed clustering cache. `results/` — gzipped job result
  blobs. `jobs.sqlite` — the job store. All gitignored. `data/` — sample inputs
  (tracked). Every path is overridable via env vars (see `config.py`).
