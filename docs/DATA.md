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
One `TaxID-SpeciesCode` per line, e.g. `00000048-Arch_geph`. Parsed by
`load_species_data` (legacy helper; not on the main tree path).

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

### Correlation matrix — `output/correlation_matrix.csv` (CLI) / `downloads/correlation_matrix.csv` (web)
Same shape as the correlation-matrix input above.

### Feature matrix — `output/feature_matrix.csv` / `downloads/feature_matrix.csv`
Rows = species, columns = domains. Each cell is a **JSON string**:
```json
{"mean_percent_identity": 92.4, "mean_alignment_length": 1579.0,
 "mean_bitscore": 2957.0, "num_hits": 1, "min_evalue": 0.0}
```
Empty (species, domain) combinations are filled with the all-zero vector of the
same keys.

### Species tree — `output/species_tree_approx.nw` / `downloads/<job_id>_<name>.nw`
Newick; leaf names are species keys; branch lengths are NJ distances in Jaccard
units.

### All-vs-all (web JSON, not a file)
`GET /allvsall_data/<f>` returns domain nodes, similarity edges, a domain × domain
co-cluster matrix, and 2-D positions. See [`API.md`](API.md).

## Where files live
- `output/` — CLI outputs. `downloads/` — web outputs. `uploads/` — uploads.
  `cache/` — scratch. All gitignored. `data/` — sample inputs (tracked).
