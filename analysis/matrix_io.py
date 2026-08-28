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
import re

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


# Enough cells to recognise the format without materialising the whole matrix:
# df.to_numpy().ravel() on the bundled feature matrix builds 183k objects just to
# answer "is this JSON?", which cost more than the parse it was preparing for.
_SNIFF_CELLS = 512


def _first_feature_cell(df):
    """The first cell that looks like a JSON feature vector, or None."""
    seen = 0
    for column in df.columns:
        for value in df[column].to_numpy()[:_SNIFF_CELLS]:
            parsed = _parse_cell(value)
            if parsed:
                return parsed
            seen += 1
            if seen >= _SNIFF_CELLS:
                return None
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
    """Return ``(rows, cols, values)`` for one metric of the matrix."""
    rows, cols, features, data = planes(path, [metric] if metric else None)
    return rows, cols, data[metric if metric in data else features[0]]


def planes(path, metrics=None):
    """
    Return ``(rows, cols, features, {metric: 2-D array})``.

    Reading every metric in one pass matters for the cell inspector, which needs
    all of them: doing it per metric would re-read and re-parse the file each
    time.
    """
    df = _read(path)
    rows = [str(i) for i in df.index]
    cols = [str(c) for c in df.columns]

    sample = _first_feature_cell(df)
    if sample is None:
        values = df.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
        return rows, cols, ["value"], {"value": _clean(values)}

    features = list(sample.keys())
    wanted = [m for m in (metrics or features) if m in features] or features[:1]
    extracted = _extract_many(df, wanted)
    return rows, cols, features, {m: _clean(v) for m, v in extracted.items()}


def _clean(values):
    return np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)


# Measured crossover on the bundled 848 x 216 feature matrix: a vectorised regex
# costs ~0.09 s per metric, while one json.loads pass costs ~0.22 s and then
# serves every metric almost free. Below the threshold the regex wins; at or
# above it, parsing once wins.
_REGEX_METRIC_LIMIT = 3
_NUMBER = r"(-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"


def _extract_many(df, metrics):
    """
    Pull numeric metrics out of a matrix of JSON cells.

    ``df.map(json.loads)`` costs one Python call per cell, and it sits on the
    path of every clustergram and embedding request. For one or two metrics --
    the common case -- a vectorised regex running in C is ~2.5x faster.

    Whichever path is taken, a cell that clearly holds the metric but yields no
    number sends us to the reference implementation, so correctness never
    depends on the shortcut.
    """
    if len(metrics) < _REGEX_METRIC_LIMIT:
        extracted = {}
        for metric in metrics:
            values = _extract_regex(df, metric)
            if values is None:
                return _extract_json(df, metrics)
            extracted[metric] = values
        return extracted
    return _extract_json(df, metrics)


def _extract_regex(df, metric):
    """One metric, vectorised. Returns None when the pattern does not fit."""
    pattern = rf'"{re.escape(metric)}"\s*:\s*{_NUMBER}'
    out = np.zeros(df.shape, dtype=float)
    for j, column in enumerate(df.columns):
        text = df[column].astype(str)
        found = text.str.extract(pattern, expand=False)
        if (found.isna() & text.str.contains(metric, regex=False)).any():
            return None
        out[:, j] = pd.to_numeric(found, errors="coerce").fillna(0.0).to_numpy()
    return out


def _extract_json(df, metrics):
    """Reference implementation: parse every cell once, then read each metric."""
    parsed = df.map(_parse_cell)
    return {m: parsed.map(lambda d, key=m: d.get(key, 0) or 0).to_numpy(dtype=float)
            for m in metrics}


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
