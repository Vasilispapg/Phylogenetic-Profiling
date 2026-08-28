"""
Reading species x domain matrices server-side.

The clustergram and embedding endpoints used to take the whole matrix inside the
JSON request body, which meant the browser parsed the CSV, re-serialised every
cell as JSON text, and posted it back. At ten times the current scale that body
exceeds MAX_CONTENT_LENGTH; even below it, it is the same data travelling twice.
Uploading the file once and referring to it by id removes both problems, and
pandas parses it far faster than PapaParse plus JSON.stringify.

Handles the two shapes the app produces: a plain numeric correlation matrix, and
a feature matrix whose cells are JSON objects.
"""
import json
import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# Refuse absurd matrices with a clear message instead of an OOM.
MAX_CELLS = 20_000_000


class MatrixError(ValueError):
    """The uploaded file is not a usable matrix."""


def _parse_cell(cell):
    """Safely parse a JSON feature-vector cell into a dict (never eval)."""
    if not isinstance(cell, str) or cell in ("", "{}"):
        return {}
    try:
        parsed = json.loads(cell)
    except (ValueError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _first_feature_cell(df):
    """The first cell that looks like a JSON feature vector, or None."""
    for value in df.to_numpy().ravel():
        parsed = _parse_cell(value)
        if parsed:
            return parsed
    return None


def describe(path):
    """
    Metadata for an uploaded matrix: labels, kind and available metrics.

    Deliberately returns no cell values -- the client already has the file it
    just uploaded, and this keeps the response O(rows + cols).
    """
    df = _read(path)
    sample = _first_feature_cell(df)
    return {
        "rows": [str(i) for i in df.index],
        "cols": [str(c) for c in df.columns],
        "kind": "feature" if sample else "numeric",
        "features": list(sample.keys()) if sample else ["value"],
    }


def plane(path, metric=None):
    """
    Return ``(rows, cols, values)`` for one metric of the matrix.

    ``metric`` is ignored for a numeric matrix and defaults to the first
    available feature otherwise.
    """
    df = _read(path)
    rows = [str(i) for i in df.index]
    cols = [str(c) for c in df.columns]

    sample = _first_feature_cell(df)
    if sample is None:
        values = df.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    else:
        if metric is None or metric not in sample:
            metric = next(iter(sample))
        values = df.map(lambda cell: _parse_cell(cell).get(metric, 0) or 0) \
                   .to_numpy(dtype=float)

    return rows, cols, np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)


def _read(path):
    try:
        df = pd.read_csv(path, index_col=0)
    except Exception as exc:                       # noqa: BLE001 - user data
        raise MatrixError(f"Could not read the CSV: {exc}") from exc
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise MatrixError("The matrix has no data rows or no columns.")
    if df.size > MAX_CELLS:
        raise MatrixError(
            f"Matrix has {df.size:,} cells, above the {MAX_CELLS:,} limit. "
            "Reduce it or run the analysis from the CLI."
        )
    return df
