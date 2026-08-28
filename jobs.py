"""
Durable job store (SQLite + WAL) shared by every blueprint.

Replaces the two incompatible in-memory models the app used to have: a uuid-keyed
``_jobs`` dict for trees and a filename-keyed pair of dicts plus a ``"Completed."``
magic string for all-vs-all. Because the state lives on disk:

* memory no longer grows without bound (results are files, not live objects),
* jobs survive a restart,
* gunicorn can run more than one worker,
* heavy work can run in a *separate process* and still report progress.
"""
import gzip
import json
import logging
import sqlite3
import time
import uuid

from config import DB_PATH, JOB_TTL_SECONDS, RESULT_DIR

log = logging.getLogger(__name__)

STATES = ("queued", "running", "done", "failed")
TERMINAL = ("done", "failed")

# A job whose worker died leaves it "running" forever; anything untouched for
# this long is swept up on the next reap().
STALE_RUNNING_SECONDS = 6 * 3600

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id       TEXT PRIMARY KEY,
  kind     TEXT NOT NULL,
  state    TEXT NOT NULL CHECK (state IN ('queued','running','done','failed')),
  progress REAL NOT NULL DEFAULT 0,
  message  TEXT,
  result   TEXT,
  error    TEXT,
  created  REAL NOT NULL,
  updated  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_created ON jobs (created);
"""

_FIELDS = ("id", "kind", "state", "progress", "message", "result", "error", "created", "updated")


def _connect():
    con = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=15000")
    return con


def init():
    """Create the schema. Idempotent; safe to call from every worker process."""
    with _connect() as con:
        con.executescript(_SCHEMA)


def create(kind, message=None):
    job_id, now = uuid.uuid4().hex, time.time()
    with _connect() as con:
        con.execute(
            "INSERT INTO jobs (id, kind, state, progress, message, created, updated) "
            "VALUES (?, ?, 'queued', 0, ?, ?, ?)",
            (job_id, kind, message, now, now),
        )
    return job_id


def update(job_id, **fields):
    """Patch a job row. Unknown keys are rejected rather than silently dropped."""
    bad = set(fields) - {"state", "progress", "message", "result", "error"}
    if bad:
        raise ValueError(f"unknown job fields: {sorted(bad)}")
    if "state" in fields and fields["state"] not in STATES:
        raise ValueError(f"invalid state: {fields['state']}")
    if "result" in fields and not isinstance(fields["result"], (str, type(None))):
        fields["result"] = json.dumps(fields["result"])
    fields["updated"] = time.time()
    assignments = ", ".join(f"{k} = ?" for k in fields)
    with _connect() as con:
        con.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", (*fields.values(), job_id))


def get(job_id):
    with _connect() as con:
        row = con.execute(
            f"SELECT {', '.join(_FIELDS)} FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
    if row is None:
        return None
    job = dict(zip(_FIELDS, row))
    if job["result"]:
        try:
            job["result"] = json.loads(job["result"])
        except ValueError:
            pass
    return job


def progress(job_id, fraction, message):
    """Report real progress from inside a worker (possibly another process)."""
    update(job_id, state="running", progress=float(fraction), message=message)


def finish(job_id, result):
    update(job_id, state="done", progress=1.0, message="Completed.", result=result)


def fail(job_id, error):
    update(job_id, state="failed", message=str(error), error=str(error))


# --- result blobs ----------------------------------------------------------
def store_blob(payload):
    """Persist a JSON-serialisable payload to disk; return its id."""
    blob_id = uuid.uuid4().hex
    (RESULT_DIR / f"{blob_id}.json.gz").write_bytes(
        gzip.compress(json.dumps(payload).encode("utf-8"))
    )
    return blob_id


def load_blob(blob_id):
    path = RESULT_DIR / f"{blob_id}.json.gz"
    if not path.exists():
        return None
    return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))


# --- housekeeping ----------------------------------------------------------
def reap(now=None):
    """
    Expire old jobs (deleting their blobs) and fail jobs whose worker vanished.

    Returns ``(expired, stranded)`` counts. Called on startup and periodically.
    """
    now = time.time() if now is None else now
    cutoff = now - JOB_TTL_SECONDS
    stale = now - STALE_RUNNING_SECONDS
    with _connect() as con:
        rows = con.execute(
            "SELECT id, result FROM jobs WHERE created < ?", (cutoff,)
        ).fetchall()
        con.execute("DELETE FROM jobs WHERE created < ?", (cutoff,))
        stranded = con.execute(
            "UPDATE jobs SET state='failed', error='Worker process disappeared.', "
            "message='Worker process disappeared.', updated=? "
            "WHERE state IN ('queued','running') AND updated < ?",
            (now, stale),
        ).rowcount
    for _, result in rows:
        _delete_blobs(result)
    if rows or stranded:
        log.info("job reap: %d expired, %d stranded", len(rows), stranded)
    return len(rows), stranded


def _delete_blobs(result):
    if not result:
        return
    try:
        data = json.loads(result)
    except ValueError:
        return
    blob_id = data.get("blob") if isinstance(data, dict) else None
    if blob_id:
        (RESULT_DIR / f"{blob_id}.json.gz").unlink(missing_ok=True)
