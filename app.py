"""PhyloFlask web application."""
import atexit
import logging
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from flask import Flask, jsonify, render_template, send_from_directory
from werkzeug.exceptions import HTTPException

import config
import jobs

config.setup_logging()
log = logging.getLogger(__name__)

app = Flask(__name__, template_folder="pages", static_folder="public")
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

jobs.init()
jobs.reap()


# ---------------------------------------------------------------------------
# Background work
#
# Heavy jobs run in a SEPARATE PROCESS. Neighbour-Joining is pure Python and holds
# the GIL, so running it as a thread inside the web worker degraded every
# concurrent request. Progress is reported through the SQLite job store, which is
# also what lets gunicorn run more than one worker now.
# ---------------------------------------------------------------------------
_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    """Lazily build the executor. JOB_BACKEND=thread is an escape hatch for
    environments where spawning subprocesses is not available."""
    global _pool
    with _pool_lock:
        if _pool is None:
            if config.JOB_BACKEND == "thread":
                log.warning("JOB_BACKEND=thread: heavy jobs will contend for the GIL")
                _pool = ThreadPoolExecutor(max_workers=config.JOB_WORKERS)
            else:
                _pool = ProcessPoolExecutor(max_workers=config.JOB_WORKERS)
            atexit.register(_pool.shutdown, wait=False)
        return _pool


def _start_reaper():
    """Expire finished jobs and their blobs on a slow timer (daemon thread)."""
    def tick():
        try:
            jobs.reap()
        except Exception:                          # noqa: BLE001 - never kill the timer
            log.exception("job reaper failed")
        finally:
            timer = threading.Timer(config.REAP_INTERVAL_SECONDS, tick)
            timer.daemon = True
            timer.start()
    timer = threading.Timer(config.REAP_INTERVAL_SECONDS, tick)
    timer.daemon = True
    timer.start()


def submit_job(kind, fn, *args, message=None):
    """Create a job row, run ``fn(job_id, *args)`` off-process, return the job id."""
    job_id = jobs.create(kind, message)
    try:
        future = _get_pool().submit(fn, job_id, *args)
    except Exception as exc:                      # pool exhausted / cannot fork
        log.exception("could not submit %s job", kind)
        jobs.fail(job_id, exc)
        return job_id
    future.add_done_callback(lambda f: _job_finished(job_id, f))
    return job_id


def _job_finished(job_id, future):
    """Catch worker crashes the worker itself could not report (OOM, segfault)."""
    try:
        future.result()
    except Exception as exc:                      # noqa: BLE001
        log.exception("job %s died", job_id)
        jobs.fail(job_id, exc)


app.submit_job = submit_job
_start_reaper()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    """Main page with navigation."""
    return render_template("index.html", active_tool="index")


@app.get("/tools")
@app.get("/tools/blast")
def blast_tool():
    """Render the BLAST analysis tool page (default)."""
    return render_template("blast.html", active_tool="blast")


@app.get("/how-to")
def how_to():
    """Step-by-step guide to using PhyloFlask."""
    return render_template("help.html", active_tool="help")


@app.get("/faq")
def faq():
    """Frequently asked questions and concepts."""
    return render_template("faq.html", active_tool="faq")


@app.get("/styleguide")
def styleguide():
    """Living design-system gallery (component templates)."""
    return render_template("styleguide.html", active_tool="styleguide")


@app.get("/health")
def health():
    """Liveness plus a cheap look at the job queue."""
    return jsonify({"status": "success", "max_upload_mb": config.MAX_UPLOAD_MB,
                    "job_workers": config.JOB_WORKERS})


# Single shared download endpoint. send_from_directory rejects path traversal.
@app.get("/downloads/<path:filename>")
def download_file(filename):
    """Download a generated result file from the downloads directory."""
    return send_from_directory(config.DOWNLOAD_DIR, filename, as_attachment=True)


# ---------------------------------------------------------------------------
# Errors: always JSON for the API, always a real status code
# ---------------------------------------------------------------------------
@app.errorhandler(HTTPException)
def http_error(exc):
    if exc.code == 413:
        message = f"Upload exceeds the {config.MAX_UPLOAD_MB} MB limit."
    else:
        message = exc.description
    return jsonify({"status": "error", "message": message}), exc.code


@app.errorhandler(Exception)
def unhandled_error(exc):
    log.exception("unhandled error")
    return jsonify({"status": "error", "message": "Internal server error."}), 500


# Tool pages (GET) and their POST handlers live in the blueprints.
from blueprints.allvsall import allvsall_bp        # noqa: E402
from blueprints.blast import blast_bp              # noqa: E402
from blueprints.heatmap import heatmap_bp          # noqa: E402
from blueprints.tree import tree_bp                # noqa: E402

app.register_blueprint(blast_bp)
app.register_blueprint(heatmap_bp)
app.register_blueprint(allvsall_bp)
app.register_blueprint(tree_bp)


if __name__ == "__main__":
    import os
    # Default 8000: on macOS port 5000 (and 7000) is taken by the AirPlay
    # Receiver (Server: AirTunes), which silently hijacks http://localhost:5000.
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 8000)),
        debug=os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes"),
    )
