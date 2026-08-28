"""Shared helpers for the JSON API blueprints."""
import os

from flask import jsonify
from werkzeug.utils import secure_filename

from config import UPLOAD_KINDS


def fail(message, code=400):
    """A JSON error response with a real HTTP status code."""
    return jsonify({"status": "error", "message": message}), code


def ok(**payload):
    """A JSON success response."""
    return jsonify({"status": "success", **payload})


def allowed(filename, kind):
    """True when ``filename``'s extension is allowed for this upload kind."""
    return os.path.splitext(filename)[1].lower() in UPLOAD_KINDS[kind]


def safe_upload_name(storage, kind):
    """
    Validate an uploaded file and return its sanitised name.

    Returns ``(name, None)`` on success or ``(None, error_response)`` so callers
    can ``return err`` directly. Every upload endpoint goes through this, which
    is what stops the tree endpoint from silently skipping the allowlist.
    """
    if storage is None or not storage.filename:
        return None, fail("No file provided.", 400)
    name = secure_filename(storage.filename)
    if not name:
        return None, fail("Invalid file name.", 400)
    if not allowed(name, kind):
        ext = os.path.splitext(name)[1].lower() or "(none)"
        allowed_list = ", ".join(sorted(UPLOAD_KINDS[kind]))
        return None, fail(f"Unsupported file type {ext} for a {kind} file. Allowed: {allowed_list}", 400)
    return name, None
