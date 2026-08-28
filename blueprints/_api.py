"""Shared helpers for the JSON API blueprints."""
import gzip
import json
import os

from flask import Response, jsonify, request
from werkzeug.utils import secure_filename

import guard
from analysis.upload_guard import RejectedUpload, stream_to_disk
from config import UPLOAD_KINDS

# Numeric payloads compress extremely well: the bundled feature matrix as a
# numeric plane is 1.0 MB of JSON but 0.06 MB gzipped.
GZIP_MIN_BYTES = 8192
GZIP_LEVEL = 6


def fail(message, code=400):
    """A JSON error response with a real HTTP status code."""
    return jsonify({"status": "error", "message": message}), code


def ok(**payload):
    """A JSON success response."""
    return jsonify({"status": "success", **payload})


def _wants_gzip():
    return "gzip" in (request.headers.get("Accept-Encoding") or "")


def gzipped_json(payload):
    """A JSON response, compressed when it is worth it and the client accepts."""
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return gzipped_bytes(body)


def gzipped_bytes(body, already_compressed=False):
    """Send pre-serialised JSON, compressing (or passing through) as appropriate."""
    if already_compressed:
        if _wants_gzip():
            response = Response(body, mimetype="application/json")
            response.headers["Content-Encoding"] = "gzip"
            return response
        body = gzip.decompress(body)
    elif _wants_gzip() and len(body) >= GZIP_MIN_BYTES:
        response = Response(gzip.compress(body, GZIP_LEVEL), mimetype="application/json")
        response.headers["Content-Encoding"] = "gzip"
        return response
    return Response(body, mimetype="application/json")


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


def save_upload(storage, kind, destination):
    """
    Validate an upload and write it to ``destination``.

    One call does the whole job: the name, the declared type, the size, and —
    the part an extension cannot tell you — whether the contents actually look
    like the format. Returns ``(name, None)`` or ``(None, error_response)``.

    A rejected upload is charged to the client that sent it: inspecting a file
    costs real work, so a caller producing a stream of malformed ones is treated
    the same as one exceeding its request budget.
    """
    name, err = safe_upload_name(storage, kind)
    if err:
        guard.strike(guard.client_ip(request), f"bad {kind} upload name/extension")
        return None, err
    try:
        size = stream_to_disk(storage, kind, destination)
    except RejectedUpload as exc:
        guard.strike(guard.client_ip(request), f"rejected {kind} upload: {exc}")
        return None, fail(str(exc), 400)
    except OSError as exc:
        return None, fail(f"Could not save the file: {exc}", 500)
    return name, None
