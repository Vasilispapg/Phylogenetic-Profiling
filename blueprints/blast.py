"""BLAST upload + matrix building."""
import logging
import os
import uuid

from flask import Blueprint, request
from werkzeug.utils import secure_filename

from analysis.matrix_operations import create_correlation_matrix, create_feature_matrix
from blueprints._api import fail, ok, safe_upload_name
from config import DOWNLOAD_DIR, UPLOAD_DIR

blast_bp = Blueprint("blast", __name__)
log = logging.getLogger(__name__)

ANALYSES = {"correlation": create_correlation_matrix, "features": create_feature_matrix}
OUTPUT_STEMS = {"correlation": "correlation_matrix", "features": "feature_matrix"}


@blast_bp.post("/upload")
def upload_file():
    """
    Store an uploaded BLAST file under a unique name.

    The returned filename carries a uuid prefix. Both front-ends treat it as an
    opaque token they hand straight back to /process, so this is invisible to
    them -- but it stops two users who happen to upload "results.blastp" from
    overwriting each other's data.
    """
    name, err = safe_upload_name(request.files.get("file"), "blast")
    if err:
        return err

    stored = f"{uuid.uuid4().hex}_{name}"
    try:
        request.files["file"].save(UPLOAD_DIR / stored)
    except OSError as exc:
        log.exception("failed to save upload %s", stored)
        return fail(f"Could not save the file: {exc}", 500)

    return ok(message="File uploaded successfully!", filename=stored, original_name=name)


@blast_bp.post("/process")
def process_file():
    """Build a correlation or feature matrix from a previously uploaded file."""
    data = request.get_json(silent=True) or {}
    filename = secure_filename(data.get("filename") or "")
    analysis_type = data.get("analysis_type")

    if not filename:
        return fail("No filename provided.", 400)
    if analysis_type not in ANALYSES:
        return fail(f"Invalid analysis type. Expected one of: {', '.join(sorted(ANALYSES))}", 400)

    input_path = UPLOAD_DIR / filename
    if not input_path.is_file():
        return fail("File not found. Upload it again.", 404)

    # A unique output name per run, for the same reason uploads get one.
    output_filename = f"{uuid.uuid4().hex}_{OUTPUT_STEMS[analysis_type]}.csv"
    try:
        ANALYSES[analysis_type](str(input_path), str(DOWNLOAD_DIR / output_filename))
    except ValueError as exc:
        return fail(str(exc), 400)

    return ok(message="Processing completed", filename=output_filename)


@blast_bp.get("/results")
def get_results():
    """Check that a processed result file exists."""
    filename = secure_filename(request.args.get("filename") or "")
    if not filename:
        return fail("Filename not provided.", 400)
    if not (DOWNLOAD_DIR / filename).is_file():
        return fail("Result file not found.", 404)
    return ok(filename=filename)
