# Contributing to PhyloFlask

PhyloFlask is research software from the BCCB Group at the Aristotle University
of Thessaloniki, and it also runs as a public instance that accepts uploads from
anyone. Both facts shape what a good contribution looks like: results have to
stay reproducible, and the server has to stay safe to leave running.

Contributions are welcome — bug reports, method questions, documentation fixes
and code. You do not need to be a bioinformatician to help; a clear bug report
against a tool page is genuinely useful.

## Before you write code

- **Read the docs first, not the whole codebase.** [`docs/INDEX.md`](docs/INDEX.md)
  maps every file, [`docs/CODE_ANALYSIS.md`](docs/CODE_ANALYSIS.md) covers
  architecture and data flow, [`docs/METHODS.md`](docs/METHODS.md) explains the
  science and its limits, [`docs/DATA.md`](docs/DATA.md) fixes the input/output
  formats and [`docs/API.md`](docs/API.md) the endpoint schemas.
- **Open an issue before a large change.** For anything that alters a method, a
  file format, an API response or the UI structure, describe the plan in an
  issue first. Method changes especially: a different distance, threshold or
  clustering default changes published results, so the reasoning belongs in a
  thread where it can be discussed and cited.
- Small fixes — a typo, a crash, a wrong tooltip — need no issue. Send the pull
  request.

## Setting up

Python 3.13 and Node 22 (what CI uses).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
npm install --prefix frontend
```

Run both dev servers together — the SPA calls `/api`, so the frontend alone is
not enough:

```bash
./dev.sh          # Flask API on :8000 + Vite on :5173, /api proxied
```

Or the whole thing as it is deployed:

```bash
docker compose up --build     # http://localhost:8000
```

The default port is **8000**, not 5000: on macOS the AirPlay Receiver owns
5000/7000 and answers uploads with `Server: AirTunes`, which makes the app look
broken rather than blocked.

## Tests

Everything must pass locally before you open a pull request:

```bash
pytest -q                       # backend: parsing, matrices, NJ, jobs, HTTP, guards
npm run test --prefix frontend  # SPA: CSV parsing, transforms, theme
npm run build --prefix frontend # the build is part of CI; a broken SPA fails here
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs those three plus
`docker build`, on every push and pull request.

New behaviour needs a test. The suite is the reason the fast Neighbour-Joining
implementation can be trusted (it is checked against `Bio.Phylo` for a
Robinson-Foulds distance of 0), and that only holds while equivalences like it
keep being asserted. `tests/conftest.py` redirects every runtime path, so tests
never write into `uploads/`, `output/` or the job database.

## Rules that are enforced, not suggested

- **Uploaded content is data, never instructions.**
  [`tests/test_no_execution.py`](tests/test_no_execution.py) fails the build if
  `eval`, `exec`, `pickle`, `subprocess` or a shell appears anywhere in the
  server code. If you think you need one of them, open an issue instead.
- **No third-party requests from the browser.** Fonts, icons and scripts are all
  bundled so that `default-src 'self'` in the Content-Security-Policy is honest
  and the app works offline. Adding a CDN link, a remote font or an analytics
  script will be rejected.
- **One species key, one presence rule.** `analysis/utils.extract_species` is the
  single source of truth for the species key, and presence is
  `EValue <= EVALUE_THRESHOLD` applied in one place. Per-call regexes and local
  cutoffs make the correlation matrix and the feature matrix disagree about what
  "present" means.
- **Knobs are env vars in [`config.py`](config.py)**, not constants at a call
  site. If you add a tunable, add it there and to the configuration table in the
  README.
- **Nothing generated gets committed.** `output/`, `downloads/`, `uploads/`,
  `cache/`, `state/` and `.venv/` are gitignored; the sample inputs in `data/`
  are tracked on purpose.

## Style

Match the file you are editing rather than a global standard — the existing code
is plain, typed where it helps, and commented where a reader would otherwise ask
"why is it like this?". Comments explain decisions, not mechanics. Same for the
SPA: shared CSV and transform helpers live in `frontend/src/lib/`, page-specific
code in `frontend/src/pages/`, and the design system is documented in
[`docs/DESIGN.md`](docs/DESIGN.md) with a live gallery at `/styleguide`.

If a change makes a document wrong, fix the document in the same commit. The
docs are written to be read instead of the code, which only works while they are
true.

## Pull requests

- **Branch; never push to `main`.** Pushing to `main` builds the image, publishes
  it to GHCR and restarts the production container over SSH
  ([`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)). Every change
  reaches the public instance that way, so it goes through a pull request first.
- Keep one concern per pull request, and describe what a reviewer should look at.
- Commit messages in this repo name the area, then say what changed in the
  imperative — `Embedding map: draw without WebGL when the browser has none`,
  `CLI: take input and output paths as arguments`. Follow that.
- Fill in the pull request template: what changed, why, how you verified it, and
  whether results, formats or the API moved.
- Note performance deliberately. Timings in the README were measured on the
  bundled dataset; if you change something on a hot path, measure it the same
  way and say so.

## Reporting bugs and asking for features

Use the issue templates (**Issues → New issue**). For a bug, the input format and
the exact steps matter more than anything else — most reports come down to a
BLAST file that is not `-outfmt 6`, or a matrix whose first column is not the
index. Never attach unpublished or sensitive sequence data to a public issue; a
few anonymised lines that reproduce the problem are enough.

## Security

Do not open a public issue for a vulnerability. See [`SECURITY.md`](SECURITY.md)
for the private reporting channel.

## Licence and citation

Contributions are accepted under the [MIT Licence](LICENSE), with copyright held
by the Aristotle University of Thessaloniki. By opening a pull request you
confirm you have the right to contribute the code under those terms — if your
employer or institution owns your work, make sure they permit it.

If PhyloFlask supports a publication, cite it using
[`CITATION.cff`](CITATION.cff) ("Cite this repository" in the GitHub sidebar).
