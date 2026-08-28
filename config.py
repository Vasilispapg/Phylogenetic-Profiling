"""Single source of truth for paths and tunable knobs.

Everything here is overridable via environment variables so the scientific
thresholds can be swept without editing code. Paths are absolute (derived from
this file's location) so the app behaves the same regardless of the working
directory gunicorn happens to be started from.
"""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent

# --- directories -----------------------------------------------------------
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", BASE / "uploads"))
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", BASE / "downloads"))
CACHE_DIR = Path(os.environ.get("CACHE_DIR", BASE / "cache"))
RESULT_DIR = Path(os.environ.get("RESULT_DIR", BASE / "results"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", BASE / "output"))
DB_PATH = Path(os.environ.get("DB_PATH", BASE / "jobs.sqlite"))

# --- web -------------------------------------------------------------------
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "200"))
JOB_TTL_SECONDS = int(os.environ.get("JOB_TTL_SECONDS", "86400"))
JOB_WORKERS = int(os.environ.get("JOB_WORKERS", "2"))
# "process" (default) runs heavy jobs off the GIL; "thread" is an escape hatch.
JOB_BACKEND = os.environ.get("JOB_BACKEND", "process").lower()
REAP_INTERVAL_SECONDS = int(os.environ.get("REAP_INTERVAL_SECONDS", "3600"))

# --- science knobs ---------------------------------------------------------
# A BLAST hit counts as "present" only at or below this E-value.
EVALUE_THRESHOLD = float(os.environ.get("EVALUE_THRESHOLD", "1e-5"))
# Minimum Jaccard similarity to draw a domain-domain edge.
JACCARD_THRESHOLD = float(os.environ.get("JACCARD_THRESHOLD", "0.5"))
# MCL granularity (higher -> more, smaller clusters).
MCL_INFLATION = float(os.environ.get("MCL_INFLATION", "2.0"))
# Leading dash-delimited segments of a SubjectID that identify a species.
SPECIES_SEGMENTS = int(os.environ.get("SPECIES_SEGMENTS", "4"))
# Refuse to build a tree above this many taxa (see MAX_TAXA guard in nj.py).
MAX_TAXA = int(os.environ.get("MAX_TAXA", "5000"))
# How many of the strongest edges /allvsall_data returns by default (times N).
EDGE_BUDGET_PER_NODE = int(os.environ.get("EDGE_BUDGET_PER_NODE", "5"))
# Default depth for every tree *display*. There used to be four different
# defaults for the same idea (64 in the CLI, 12 and 4 in display_tree, 4 in the
# viewer), which made "depth" mean something different in each place.
TREE_DISPLAY_DEPTH = int(os.environ.get("TREE_DISPLAY_DEPTH", "6"))
TREE_DISPLAY_MAX_DEPTH = int(os.environ.get("TREE_DISPLAY_MAX_DEPTH", "30"))

# --- upload validation -----------------------------------------------------
UPLOAD_KINDS = {
    "blast": {".blastp", ".tsv", ".tab", ".txt", ".out", ".csv"},
    "matrix": {".csv", ".tsv", ".txt"},
    "newick": {".nw", ".newick", ".nwk", ".txt"},
}

for _d in (UPLOAD_DIR, DOWNLOAD_DIR, CACHE_DIR, RESULT_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def setup_logging():
    """Configure root logging once. Safe to call from app.py and main.py."""
    import logging
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)-7s %(name)s [%(threadName)s] %(message)s",
    )
