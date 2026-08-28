"""Server-side clustering and embedding for the heatmap family of tools."""
import gzip
import hashlib
import json
import logging

from flask import Blueprint, request

from analysis import matrix_io
from blueprints._api import fail, gzipped_bytes, ok
from blueprints.matrices import resolve
from config import CACHE_DIR

heatmap_bp = Blueprint("heatmap", __name__)
log = logging.getLogger(__name__)

MIN_POINTS = 3   # fewer than this and clustering/embedding are meaningless

# Both endpoints are deterministic (t-SNE and KMeans are seeded), and the UI
# re-requests them on every metric / axis / method / k change. Caching on the
# inputs turns those repeats into a file read.
CACHE_VERSION = 1


def _cached(kind, key_parts, compute):
    """Return a cached response for these inputs, computing it on a miss."""
    digest = hashlib.sha256(
        json.dumps([kind, CACHE_VERSION, key_parts], sort_keys=True, default=str).encode()
    ).hexdigest()
    path = CACHE_DIR / f"{kind}-{digest}.json.gz"
    if path.exists():
        log.debug("%s cache hit", kind)
        return gzipped_bytes(path.read_bytes(), already_compressed=True)

    payload, err = compute()
    if err:
        return err
    body = json.dumps({"status": "success", **payload}, separators=(",", ":")).encode()
    path.write_bytes(gzip.compress(body, 6))
    return gzipped_bytes(body)


def _fingerprint(payload):
    """Identify the input: a matrix id + metric, or a hash of an inline matrix."""
    if payload.get("file_id"):
        return {"file_id": payload["file_id"], "metric": payload.get("metric")}
    return {"z": hashlib.sha256(
        json.dumps(payload.get("z"), separators=(",", ":")).encode()).hexdigest()}


def _matrix(payload):
    """
    Resolve the matrix to work on. Returns (array, None) or (None, error).

    Preferred: ``{"file_id": "..."}`` referring to a matrix uploaded to
    /matrices, so the values never travel in a request body. ``{"z": [[...]]}``
    is still accepted for small ad-hoc matrices and for the CLI/tests.
    """
    import numpy as np

    file_id = payload.get("file_id")
    if file_id:
        path = resolve(file_id)
        if path is None:
            return None, fail("Unknown matrix id. Upload the file again.", 404)
        try:
            _rows, _cols, values = matrix_io.plane(path, payload.get("metric"))
        except matrix_io.MatrixError as exc:
            return None, fail(str(exc), 400)
        return values, None

    z = payload.get("z")
    if not z or not isinstance(z, list) or not z[0]:
        return None, fail("No matrix provided: pass file_id or z.", 400)
    try:
        m = np.asarray(z, dtype=float)
    except (TypeError, ValueError):
        return None, fail("Matrix must be numeric and rectangular.", 400)
    if m.ndim != 2:
        return None, fail("Matrix must be two-dimensional.", 400)
    if m.size > matrix_io.MAX_CELLS:
        return None, fail(
            f"Matrix has {m.size:,} cells, above the {matrix_io.MAX_CELLS:,} limit. "
            "Upload it to /matrices and pass file_id instead.", 413)
    return m, None


@heatmap_bp.post("/clustergram")
def clustergram():
    """Hierarchically cluster an uploaded numeric matrix (rows x cols) and return
    leaf orders + dendrogram line coordinates for both axes (drawn client-side)."""
    import numpy as np
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import pdist

    payload = request.get_json(silent=True) or {}

    def compute():
        m, err = _matrix(payload)
        if err:
            return None, err
        row_order, row_dendro = cluster(m)
        col_order, col_dendro = cluster(m.T)
        return {"row_order": row_order, "col_order": col_order,
                "row_dendro": row_dendro, "col_dendro": col_dendro}, None

    def cluster(a):
        n = a.shape[0]
        if n < MIN_POINTS:
            return list(range(n)), {"icoord": [], "dcoord": []}
        # correlation distance groups by profile *shape* (co-occurrence); constant
        # rows have undefined correlation -> treat as maximally distant.
        d = pdist(a, metric="correlation")
        d = np.nan_to_num(d, nan=1.0, posinf=1.0, neginf=1.0)
        dn = dendrogram(linkage(d, method="average"), no_plot=True)
        return [int(i) for i in dn["leaves"]], {"icoord": dn["icoord"], "dcoord": dn["dcoord"]}

    return _cached("clustergram", _fingerprint(payload), compute)


@heatmap_bp.post("/embedding")
def embedding():
    """Project domains (columns) or species (rows) into 2D by their co-occurrence
    profile (PCA or t-SNE) and colour by a KMeans clustering of the profiles."""
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE
    from sklearn.preprocessing import StandardScaler

    payload = request.get_json(silent=True) or {}
    axis = payload.get("axis", "domains")
    method = payload.get("method", "pca")
    if method not in ("pca", "tsne"):
        return fail("Method must be 'pca' or 'tsne'.", 400)
    try:
        k = int(payload.get("k", 8))
    except (TypeError, ValueError):
        return fail("k must be an integer.", 400)

    def compute():
        m, err = _matrix(payload)
        if err:
            return None, err

        x = m.T if axis == "domains" else m       # points = rows of x
        n = x.shape[0]
        if n < MIN_POINTS:
            return None, fail(f"Need at least {MIN_POINTS} points to embed, got {n}.", 400)

        xs = StandardScaler().fit_transform(x)
        xs = np.nan_to_num(xs, nan=0.0, posinf=0.0, neginf=0.0)

        try:
            if method == "tsne":
                perplexity = max(5, min(30, (n - 1) // 3))
                coords = TSNE(n_components=2, init="pca", perplexity=perplexity,
                              learning_rate="auto", random_state=42).fit_transform(xs)
            else:
                coords = PCA(n_components=2).fit_transform(xs)
            labels = KMeans(n_clusters=max(2, min(k, n - 1)), n_init=10,
                            random_state=42).fit_predict(xs)
        except ValueError as exc:
            return None, fail(str(exc), 400)

        return {"coords": coords.tolist(), "labels": [int(v) for v in labels],
                "n_clusters": int(max(labels) + 1)}, None

    return _cached("embedding", {**_fingerprint(payload), "axis": axis,
                                 "method": method, "k": k}, compute)
