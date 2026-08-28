"""Upload a matrix once, then refer to it by id."""
import logging
import uuid

from flask import Blueprint, request
from werkzeug.utils import secure_filename

from analysis import matrix_io
from blueprints._api import fail, ok, safe_upload_name
from config import UPLOAD_DIR

matrices_bp = Blueprint("matrices", __name__)
log = logging.getLogger(__name__)


def resolve(file_id):
    """Map a matrix id to its path, refusing anything that is not one of ours."""
    safe = secure_filename(file_id or "")
    if not safe:
        return None
    path = UPLOAD_DIR / safe
    return path if path.is_file() else None


@matrices_bp.post("/matrices")
def upload_matrix():
    """Store a matrix CSV and return its id plus enough metadata to drive the UI."""
    name, err = safe_upload_name(request.files.get("file"), "matrix")
    if err:
        return err

    file_id = f"{uuid.uuid4().hex}_{name}"
    path = UPLOAD_DIR / file_id
    try:
        request.files["file"].save(path)
    except OSError as exc:
        log.exception("failed to save matrix %s", file_id)
        return fail(f"Could not save the file: {exc}", 500)

    try:
        meta = matrix_io.describe(path)
    except matrix_io.MatrixError as exc:
        path.unlink(missing_ok=True)
        return fail(str(exc), 400)

    return ok(file_id=file_id, name=name, **meta)
