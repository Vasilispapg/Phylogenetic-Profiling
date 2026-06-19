# Phylogenetic Profiling

A Flask web app (with a parallel CLI) for **phylogenetic profiling** of protein
domains across species, starting from a BLAST tabular file. It builds
species × domain presence/absence matrices and from them:

- a **Neighbour-Joining species tree** (Jaccard distance between domain profiles),
- **domain clusters** (Markov Clustering on a domain × domain profile-similarity
  graph) with a **clustering-quality validation report**,
- interactive **heatmaps** and an **all-vs-all graph** in the browser.

> New to the code? Read [`INDEX.md`](INDEX.md) (file map) and
> [`CODE_ANALYSIS.md`](CODE_ANALYSIS.md) (architecture, data flow, methods,
> limitations) — they describe what the code does now without re-reading it all.

## Tools (web)

| Page | Route | What it does |
|------|-------|--------------|
| BLAST Analysis | `/tools/blast` | Upload a BLAST file → build correlation or feature matrix (downloadable) |
| Heatmap | `/tools/heatmap` | Upload a matrix CSV → interactive heatmaps (client-side: Plotly/ECharts) |
| All vs All | `/tools/allvsall` | Upload a correlation matrix → MCL domain clusters + graph/heatmap |
| Tree Construct | `/tools/tree_construct` | Upload a correlation matrix → NJ tree (Newick), async job + polling |
| Tree Viewer | `/tools/tree_viewer` | Upload a `.nw` file → interactive radial D3 tree |

## Quick start

### Docker (recommended)
```bash
docker compose up --build
# open http://localhost:5000
```
Uploaded/generated files persist in `./uploads`, `./downloads`, `./cache`.

### Local (Python 3.13)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py                 # dev server on http://127.0.0.1:5000
# production:
gunicorn --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:5000 app:app
```
Run **1 worker** (threads for concurrency): job state is in-memory, so multiple
workers would not share it. See [`CODE_ANALYSIS.md`](CODE_ANALYSIS.md).

## CLI

```bash
python main.py <command>
```

| Command | Action |
|---------|--------|
| `--analyze` | Build `output/correlation_matrix.csv` and `output/feature_matrix.csv` from the bundled BLAST file |
| `--construct_tree` | Build a NJ tree from the correlation matrix → `output/species_tree_approx.nw` |
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
- A hit counts as **present** only when `EValue <= 1e-5` (configurable).

## Configuration (env vars)

| Var | Default | Meaning |
|-----|---------|---------|
| `PORT` / `HOST` | `5000` / `127.0.0.1` | Dev server bind |
| `FLASK_DEBUG` | `0` (off) | Enable Flask debugger (never in production) |
| `MAX_UPLOAD_MB` | `200` | Max upload size |
| `DASH_DEBUG` | off | Debug mode for standalone Dash apps |

## Testing

```bash
pip install pytest
pytest -q
```
Covers species-key extraction, matrix building, true-positive extraction,
Jaccard distance/tree, domain clustering + validation, and Flask route/security
smoke tests.

## Project layout

```
app.py                  Flask app factory, page routes, shared download endpoint
main.py                 CLI entry point
templates/*.py          Flask blueprints (blast, heatmap, allvsall, tree)
analysis/               BLAST parsing, matrices, MCL clustering + validation
tree_construction/      Distance matrix + NJ tree + circular tree display
visualization/          Plotly/Dash heatmaps
pages/*.html            Jinja templates (tools.html is the base layout)
public/                 Static assets (CSS/JS/images)
data/                   Sample inputs (species lists + BLAST file)
tests/                  pytest suite
Dockerfile, docker-compose.yml
```
