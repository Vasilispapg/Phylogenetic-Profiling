import os

from flask import Blueprint, jsonify, render_template, request

# Blueprint for heatmap routes
heatmap_bp = Blueprint('heatmap', __name__, template_folder='templates')

UPLOAD_FOLDER = './uploads'
CACHE_FOLDER = './cache'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)


@heatmap_bp.route('/tools/heatmap', methods=['GET'])
def heatmap_tool():
    """
    Render the heatmap tool page. The page processes uploaded CSV matrices
    entirely client-side (PapaParse / d3 + Plotly / ECharts), so no data
    endpoint is required here.
    """
    return render_template('heatmap.html', active_tool="heatmap")


@heatmap_bp.route('/clustergram', methods=['POST'])
def clustergram():
    """Hierarchically cluster an uploaded numeric matrix (rows x cols) and return
    leaf orders + dendrogram line coordinates for both axes (drawn client-side)."""
    import numpy as np
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import pdist

    payload = request.get_json(silent=True) or {}
    z = payload.get('z')
    if not z or not isinstance(z, list) or not z[0]:
        return jsonify({"status": "error", "message": "No matrix provided."})

    try:
        m = np.asarray(z, dtype=float)
    except Exception:
        return jsonify({"status": "error", "message": "Matrix must be numeric."})

    def cluster(a):
        n = a.shape[0]
        if n < 3:
            return list(range(n)), {"icoord": [], "dcoord": []}
        # correlation distance groups by profile *shape* (co-occurrence); constant
        # rows have undefined correlation -> treat as maximally distant.
        d = pdist(a, metric='correlation')
        d = np.nan_to_num(d, nan=1.0, posinf=1.0, neginf=1.0)
        linkage_matrix = linkage(d, method='average')
        dn = dendrogram(linkage_matrix, no_plot=True)
        return [int(i) for i in dn['leaves']], {"icoord": dn['icoord'], "dcoord": dn['dcoord']}

    row_order, row_dendro = cluster(m)
    col_order, col_dendro = cluster(m.T)
    return jsonify({
        "status": "success",
        "row_order": row_order, "col_order": col_order,
        "row_dendro": row_dendro, "col_dendro": col_dendro,
    })


@heatmap_bp.route('/embedding', methods=['POST'])
def embedding():
    """Project domains (columns) or species (rows) into 2D by their co-occurrence
    profile (PCA or t-SNE) and colour by a KMeans clustering of the profiles."""
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE
    from sklearn.preprocessing import StandardScaler

    payload = request.get_json(silent=True) or {}
    z = payload.get('z')
    if not z or not isinstance(z, list) or not z[0]:
        return jsonify({"status": "error", "message": "No matrix provided."})

    axis = payload.get('axis', 'domains')
    method = payload.get('method', 'pca')
    k = int(payload.get('k', 8))

    try:
        m = np.asarray(z, dtype=float)
    except Exception:
        return jsonify({"status": "error", "message": "Matrix must be numeric."})

    x = m.T if axis == 'domains' else m       # points = rows of x
    n = x.shape[0]
    if n < 3:
        return jsonify({"status": "error", "message": "Need at least 3 points to embed."})

    xs = StandardScaler().fit_transform(x)
    xs = np.nan_to_num(xs, nan=0.0, posinf=0.0, neginf=0.0)

    try:
        if method == 'tsne':
            perplexity = max(5, min(30, (n - 1) // 3))
            coords = TSNE(n_components=2, init='pca', perplexity=perplexity,
                          learning_rate='auto', random_state=42).fit_transform(xs)
        else:
            coords = PCA(n_components=2).fit_transform(xs)
        kk = max(2, min(k, n - 1))
        labels = KMeans(n_clusters=kk, n_init=10, random_state=42).fit_predict(xs)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

    return jsonify({
        "status": "success",
        "coords": coords.tolist(),
        "labels": [int(v) for v in labels],
        "n_clusters": int(max(labels) + 1),
    })
