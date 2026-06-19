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
- interactive **heatmaps** (Plotly/ECharts) in the browser.

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
| BLAST Analysis | `/tools/blast` | Upload a BLAST file → build correlation or feature matrix (downloadable) |
| Heatmap | `/tools/heatmap` | Upload a matrix CSV → interactive heatmaps (order/log toggles, cell-click, zoom, PNG) |
| All vs All | `/tools/allvsall` | Upload a correlation matrix → MCL clusters: network coloured by cluster + linked co-cluster heatmap |
| Tree builder | `/tools/tree_construct` | Upload a correlation matrix → NJ tree (Newick), async job + polling |
| Tree viewer | `/tools/tree_viewer` | Upload a `.nw` file → collapsible radial tree (genus colours, search) |
| How to use | `/how-to` | Per-tool walkthrough |
| FAQ | `/faq` | Concepts, methods, troubleshooting, credits |

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
gunicorn --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:8000 app:app
```

> **macOS note:** the default port is **8000**, not 5000 — on macOS the AirPlay
> Receiver (System Settings → General → AirDrop & Handoff) occupies ports 5000
> and 7000 and will silently answer with `Server: AirTunes`, making the app look
> broken. Use 8000, or disable the AirPlay Receiver.
Run **1 worker** (threads for concurrency): job state is in-memory, so multiple
workers would not share it. See [`docs/CODE_ANALYSIS.md`](docs/CODE_ANALYSIS.md).

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
| `PORT` / `HOST` | `8000` / `127.0.0.1` | Dev server bind (5000 clashes with macOS AirPlay) |
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
