"""All-vs-all domain clustering (MCL), as a background job."""
import logging
import uuid

import jobs
from flask import Blueprint, current_app, render_template, request

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


@allvsall_bp.route("/tools/allvsall", methods=["GET", "POST"])
def allvsall_tool():
    """Render the all-vs-all page, or start a clustering job."""
    if request.method == "GET":
        return render_template("allvsall.html", active_tool="allvsall")

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
    # `filename` is the legacy handle both front-ends round-trip; it is now the
    # job id, so status and data lookups can no longer collide between users.
    return ok(message="File uploaded and processing started.",
              filename=job_id, job_id=job_id)


@allvsall_bp.get("/allvsall_status/<path:filename>")
def allvsall_status(filename):
    """
    Poll a clustering job. `filename` is the job id returned by the upload.

    A failed *job* is still a successful *request*, so this returns 200 with
    ``state="failed"``. Only a genuinely bad request (unknown job) is a 4xx.
    """
    job = jobs.get(filename)
    if job is None or job["kind"] != "allvsall":
        return fail("No process found for this file.", 404)
    message = LEGACY_DONE if job["state"] == "done" else (job["message"] or "Working...")
    return ok(message=message, state=job["state"], progress=job["progress"])


@allvsall_bp.get("/allvsall_data/<path:filename>")
def get_allvsall_data(filename):
    """
    Fetch the finished clustering payload.

    Add ``?include=matrix,positions`` for the O(n^2) extras (the co-cluster
    matrix and a spring layout). New clients derive the matrix from
    ``node_cluster`` and run their own layout, so they never need them.
    """
    job = jobs.get(filename)
    if job is None or job["kind"] != "allvsall":
        return fail("Data not found for this file.", 404)
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
