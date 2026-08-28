"""All-vs-all domain clustering (MCL), as a background job."""
import logging
import uuid

import jobs
from flask import Blueprint, current_app, request

from blueprints._api import fail, ok, safe_upload_name
from config import UPLOAD_DIR

allvsall_bp = Blueprint("allvsall", __name__)
log = logging.getLogger(__name__)

# Legacy display string. Clients must branch on the machine-readable `state`
# field; this is kept only so old cached front-ends still show sensible text.
LEGACY_DONE = "Completed."

# Fields that are O(n^2) on the wire and fully derivable client-side. They are
# held in the result blob but only serialised when a client explicitly asks, so
# the default payload stays O(n).
OPTIONAL_FIELDS = ("matrix", "positions")


@allvsall_bp.post("/allvsall")
def allvsall_tool():
    """Start a clustering job from an uploaded correlation matrix."""
    name, err = safe_upload_name(request.files.get("file"), "matrix")
    if err:
        return err

    stored = f"{uuid.uuid4().hex}_{name}"
    try:
        request.files["file"].save(UPLOAD_DIR / stored)
    except OSError as exc:
        log.exception("failed to save upload %s", stored)
        return fail(f"Could not save the file: {exc}", 500)

    from workers import run_allvsall_job
    job_id = current_app.submit_job(
        "allvsall", run_allvsall_job, str(UPLOAD_DIR / stored),
        message="Queued for clustering...",
    )
    return ok(message="File uploaded and processing started.", job_id=job_id)


@allvsall_bp.get("/allvsall/<job_id>/status")
def allvsall_status(job_id):
    """
    Poll a clustering job.

    A failed *job* is still a successful *request*, so this returns 200 with
    ``state="failed"``. Only a genuinely bad request (unknown job) is a 4xx.
    """
    job = jobs.get(job_id)
    if job is None or job["kind"] != "allvsall":
        return fail("No clustering job with that id.", 404)
    message = LEGACY_DONE if job["state"] == "done" else (job["message"] or "Working...")
    return ok(message=message, state=job["state"], progress=job["progress"])


@allvsall_bp.get("/allvsall/<job_id>/data")
def get_allvsall_data(job_id):
    """
    Fetch the finished clustering payload.

    Add ``?include=matrix,positions`` for the O(n^2) extras (the co-cluster
    matrix and a spring layout). New clients derive the matrix from
    ``node_cluster`` and run their own layout, so they never need them.
    """
    job = jobs.get(job_id)
    if job is None or job["kind"] != "allvsall":
        return fail("No clustering job with that id.", 404)
    if job["state"] == "failed":
        return fail(job["message"] or "Clustering failed.", 422)
    if job["state"] != "done":
        return fail("Clustering is still running.", 409)

    payload = jobs.load_blob((job["result"] or {}).get("blob"))
    if payload is None:
        return fail("The result has expired. Please upload the matrix again.", 410)

    wanted = {f.strip() for f in (request.args.get("include") or "").split(",")}
    lean = {k: v for k, v in payload.items()
            if k not in OPTIONAL_FIELDS or k in wanted}
    return ok(**lean)
