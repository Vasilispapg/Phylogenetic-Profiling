"""Upload a matrix once, then refer to it by id."""
import logging
import uuid

from flask import Blueprint, request
from werkzeug.utils import secure_filename

from analysis import matrix_io
from blueprints._api import fail, gzipped_json, ok, save_upload
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
    token = uuid.uuid4().hex
    name, err = save_upload(request.files.get("file"), "matrix", UPLOAD_DIR / token)
    if err:
        return err
    file_id = f"{token}_{name}"
    path = UPLOAD_DIR / file_id
    (UPLOAD_DIR / token).rename(path)

    try:
        meta = matrix_io.describe(path)
    except matrix_io.MatrixError as exc:
        path.unlink(missing_ok=True)
        return fail(str(exc), 400)

    return ok(file_id=file_id, name=name, **meta)


@matrices_bp.get("/matrices/<file_id>/plane")
def matrix_plane(file_id):
    """
    The matrix as numbers, so the browser never has to parse the CSV.

    A feature matrix stores a JSON object per cell: the bundled one is a 25 MB
    file that the client used to download and parse with PapaParse plus a
    JSON.parse per cell. The same data as numeric planes is 1.0 MB of JSON and
    0.06 MB gzipped -- around 400x less over the wire, and no parsing in JS.

    ``?metrics=a,b`` selects columns of a feature matrix; the default is all of
    them, which is what the cell inspector needs.
    """
    path = resolve(file_id)
    if path is None:
        return fail("Unknown matrix id. Upload the file again.", 404)

    requested = request.args.get("metrics")
    metrics = [m.strip() for m in requested.split(",") if m.strip()] if requested else None
    try:
        rows, cols, features, data = matrix_io.planes(path, metrics)
    except matrix_io.MatrixError as exc:
        return fail(str(exc), 400)

    return gzipped_json({
        "status": "success",
        "rows": rows,
        "cols": cols,
        "features": features,
        "kind": "feature" if features != ["value"] else "numeric",
        "data": {m: v.tolist() for m, v in data.items()},
    })
