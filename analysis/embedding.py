"""
2D projection of a species x domain matrix: the maths behind the embedding map.

This used to live inside the /embedding endpoint. It is out here so the CLI runs
the same projection the web serves rather than a second copy of it -- the
blueprint keeps what is genuinely web (request parsing, caching, status codes).

No UI framework and no Flask import, for the same reason clustering_analysis.py
has none: importing this must not drag a web stack in.
"""
import logging

import numpy as np

log = logging.getLogger(__name__)

METHODS = ("pca", "tsne")
AXES = ("domains", "species")

MIN_POINTS = 3   # fewer than this and clustering/embedding are meaningless
# Below this, t-SNE still runs but its layout carries no information.
TSNE_MEANINGFUL = 10


def embed(matrix, axis="domains", method="pca", k=8):
    """
    Project one axis of a species x domain matrix into 2D, coloured by KMeans.

    ``axis="domains"`` projects the columns (a point per domain, positioned by
    the species it occurs in), ``axis="species"`` the rows. ``k`` is the number
    of KMeans clusters used for colour, clamped to what the point count allows.

    Returns ``{"coords", "labels", "n_clusters"}``, plus a ``note`` when the
    result is technically valid but says nothing. Raises ``ValueError`` for an
    unknown method/axis, too few points, or a matrix scikit-learn rejects.

    Both estimators are seeded, so the same matrix always gives the same picture
    -- which is what makes the endpoint's cache and a CLI rerun agree.
    """
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE
    from sklearn.preprocessing import StandardScaler

    if method not in METHODS:
        raise ValueError(f"Method must be one of: {', '.join(METHODS)}.")
    if axis not in AXES:
        raise ValueError(f"Axis must be one of: {', '.join(AXES)}.")

    x = np.asarray(matrix, dtype=float)
    x = x.T if axis == "domains" else x           # points = rows of x
    n = x.shape[0]
    if n < MIN_POINTS:
        raise ValueError(f"Need at least {MIN_POINTS} points to embed, got {n}.")

    xs = StandardScaler().fit_transform(x)
    xs = np.nan_to_num(xs, nan=0.0, posinf=0.0, neginf=0.0)

    if method == "tsne":
        # scikit-learn requires perplexity < n_samples. The old floor of 5 broke
        # every projection of 5 points or fewer, which is exactly the size of a
        # small domain set.
        perplexity = min(30.0, max(1.0, (n - 1) / 3.0), n - 1)
        coords = TSNE(n_components=2, init="pca", perplexity=perplexity,
                      learning_rate="auto", random_state=42).fit_transform(xs)
    else:
        # Seeded on purpose: at these shapes scikit-learn picks the *randomized*
        # SVD solver, so an unseeded PCA gives visibly different coordinates for
        # the same matrix on every cache miss -- and the CLI and the web would
        # disagree about the same input.
        coords = PCA(n_components=2, random_state=42).fit_transform(xs)
    labels = KMeans(n_clusters=max(2, min(k, n - 1)), n_init=10,
                    random_state=42).fit_predict(xs)

    result = {"coords": coords.tolist(), "labels": [int(v) for v in labels],
              "n_clusters": int(max(labels) + 1)}
    if method == "tsne" and n < TSNE_MEANINGFUL:
        # It runs, but say so: at this size the layout is arbitrary.
        result["note"] = (f"t-SNE on {n} points says little about structure — "
                          f"PCA is the more honest read here.")
    return result
