"""PhyloFlask web application."""
import atexit
import logging
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

import config
import guard
import jobs

config.setup_logging()
log = logging.getLogger(__name__)

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

jobs.init()
jobs.reap()
guard.init()


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
                from workers import warm_up
                _pool = ProcessPoolExecutor(max_workers=config.JOB_WORKERS,
                                            initializer=warm_up)
            atexit.register(_pool.shutdown, wait=False)
        return _pool


def _start_reaper():
    """Expire finished jobs and their blobs on a slow timer (daemon thread)."""
    def tick():
        try:
            jobs.reap()
            guard.forget_old()
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
# React SPA
#
# The single UI. The server-rendered Jinja pages that used to duplicate every
# tool were removed: they had drifted (three tools existed only in React), and
# maintaining two implementations of the same API client was the largest source
# of duplication in the repo.
# ---------------------------------------------------------------------------
DIST = config.BASE / "frontend" / "dist"

API_PREFIX = "/api"


@app.get("/api/health")
def health():
    """Liveness plus a cheap look at the job queue."""
    return jsonify({"status": "success", "max_upload_mb": config.MAX_UPLOAD_MB,
                    "job_workers": config.JOB_WORKERS,
                    "spa_built": (DIST / "index.html").is_file()})


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def spa(path):
    """
    Serve the built bundle, falling back to index.html for client-side routes.

    Every JSON endpoint lives under /api, so a React route can never collide with
    one -- which it did: /clustergram and /embedding were both a page and an
    endpoint, and the endpoint won. An unmatched /api path must 404 as JSON
    rather than fall through to index.html, or a typo in a client would look
    like a successful request returning HTML.
    """
    if path == "api" or path.startswith("api/"):
        abort(404)
    if not (DIST / "index.html").is_file():
        return jsonify({
            "status": "error",
            "message": "The React bundle is not built. Run: npm ci --prefix frontend "
                       "&& npm run build --prefix frontend",
        }), 503
    if path and (DIST / path).is_file():
        return send_from_directory(DIST, path)
    # A missing file with an extension is a broken asset reference, not a
    # client-side route: 404 it instead of quietly answering with index.html,
    # which turns a typo'd bundle path into a confusing HTML-parse error.
    if "." in path.rsplit("/", 1)[-1]:
        abort(404)
    return send_from_directory(DIST, "index.html")


# Single shared download endpoint. send_from_directory rejects path traversal.
@app.get("/api/downloads/<path:filename>")
def download_file(filename):
    """Download a generated result file from the downloads directory."""
    return send_from_directory(config.DOWNLOAD_DIR, filename, as_attachment=True)


# ---------------------------------------------------------------------------
# Abuse limits
#
# nginx limits at the edge in production, but the app should not depend on being
# deployed behind it. These are the endpoints that start work; everything else
# under /api is polling and reading results, which is frequent and cheap.
# ---------------------------------------------------------------------------
HEAVY_ENDPOINTS = frozenset({
    "/api/upload", "/api/process", "/api/matrices",
    "/api/allvsall", "/api/trees", "/api/newick",
})


@app.before_request
def rate_limit():
    if not request.path.startswith("/api/"):
        return None
    bucket = "heavy" if request.method == "POST" and request.path in HEAVY_ENDPOINTS else "api"
    verdict = guard.check(guard.client_ip(request), bucket)
    if verdict.allowed:
        return None
    response = jsonify({"status": "error", "message": verdict.reason})
    response.status_code = 429
    response.headers["Retry-After"] = str(verdict.retry_after)
    return response


@app.after_request
def security_headers(response):
    """
    The app loads nothing from anywhere else, so it can say so.

    Fonts, icons and every script are bundled, which makes a strict policy
    honest rather than aspirational. Inline *styles* are still allowed because
    the UI sets element style attributes; inline *scripts* are not.
    """
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Content-Security-Policy", "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]))
    return response


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
from blueprints.matrices import matrices_bp      # noqa: E402
from blueprints.tree import tree_bp                # noqa: E402

for _bp in (blast_bp, heatmap_bp, matrices_bp, allvsall_bp, tree_bp):
    app.register_blueprint(_bp, url_prefix=API_PREFIX)


if __name__ == "__main__":
    import os
    # Default 8000: on macOS port 5000 (and 7000) is taken by the AirPlay
    # Receiver (Server: AirTunes), which silently hijacks http://localhost:5000.
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 8000)),
        debug=os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes"),
    )
