import os
import sys
import tempfile

# Make the project root importable when running `pytest` from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Point every runtime directory at a scratch dir BEFORE config is imported, so a
# test run never touches the developer's uploads/, downloads/ or job database.
_SCRATCH = tempfile.mkdtemp(prefix="phyloflask-tests-")
os.environ.setdefault("UPLOAD_DIR", os.path.join(_SCRATCH, "uploads"))
os.environ.setdefault("DOWNLOAD_DIR", os.path.join(_SCRATCH, "downloads"))
os.environ.setdefault("CACHE_DIR", os.path.join(_SCRATCH, "cache"))
os.environ.setdefault("RESULT_DIR", os.path.join(_SCRATCH, "results"))
os.environ.setdefault("OUTPUT_DIR", os.path.join(_SCRATCH, "output"))
os.environ.setdefault("DB_PATH", os.path.join(_SCRATCH, "jobs.sqlite"))
