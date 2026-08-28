"""Client-side heatmap page plus the two server-side maths endpoints."""
import logging

from flask import Blueprint, render_template, request

from blueprints._api import fail, ok

heatmap_bp = Blueprint("heatmap", __name__)
log = logging.getLogger(__name__)

MIN_POINTS = 3          # fewer than this and clustering/embedding are meaningless
MAX_CELLS = 20_000_000  # refuse absurd matrices with a clear message, not an OOM


def _matrix(payload):
    """Validate and convert the posted matrix. Returns (array, None) or (None, error)."""
    import numpy as np

    z = payload.get("z")
    if not z or not isinstance(z, list) or not z[0]:
        return None, fail("No matrix provided.", 400)
    try:
        m = np.asarray(z, dtype=float)
    except (TypeError, ValueError):
        return None, fail("Matrix must be numeric and rectangular.", 400)
    if m.ndim != 2:
        return None, fail("Matrix must be two-dimensional.", 400)
    if m.size > MAX_CELLS:
        return None, fail(
            f"Matrix has {m.size:,} cells, above the {MAX_CELLS:,} limit. "
            "Reduce the matrix or run the analysis from the CLI.", 413)
    return m, None


@heatmap_bp.get("/tools/heatmap")
def heatmap_tool():
    """
    Render the heatmap tool page. The page processes uploaded CSV matrices
    entirely client-side (PapaParse / d3 + Plotly / ECharts), so no data
    endpoint is required here.
    """
    return render_template("heatmap.html", active_tool="heatmap")


@heatmap_bp.post("/clustergram")
def clustergram():
    """Hierarchically cluster an uploaded numeric matrix (rows x cols) and return
    leaf orders + dendrogram line coordinates for both axes (drawn client-side)."""
    import numpy as np
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import pdist

    m, err = _matrix(request.get_json(silent=True) or {})
    if err:
        return err

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

    row_order, row_dendro = cluster(m)
    col_order, col_dendro = cluster(m.T)
    return ok(row_order=row_order, col_order=col_order,
              row_dendro=row_dendro, col_dendro=col_dendro)


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
    m, err = _matrix(payload)
    if err:
        return err

    axis = payload.get("axis", "domains")
    method = payload.get("method", "pca")
    if method not in ("pca", "tsne"):
        return fail("Method must be 'pca' or 'tsne'.", 400)
    try:
        k = int(payload.get("k", 8))
    except (TypeError, ValueError):
        return fail("k must be an integer.", 400)

    x = m.T if axis == "domains" else m       # points = rows of x
    n = x.shape[0]
    if n < MIN_POINTS:
        return fail(f"Need at least {MIN_POINTS} points to embed, got {n}.", 400)

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
        return fail(str(exc), 400)

    return ok(coords=coords.tolist(), labels=[int(v) for v in labels],
              n_clusters=int(max(labels) + 1))
