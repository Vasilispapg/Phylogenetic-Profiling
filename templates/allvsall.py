import os
import threading
from threading import Lock

from flask import Blueprint, jsonify, render_template, request
from werkzeug.utils import secure_filename
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from analysis.clustering_analysis import cluster_domains

# Blueprint for allvsall routes
allvsall_bp = Blueprint('allvsall', __name__, template_folder='templates')

UPLOAD_FOLDER = './uploads'
CACHE_FOLDER = './cache'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'.csv', '.tsv', '.txt'}

# Shared state guarded by a single lock.
precomputed_results = {}
progress_status = {}
_lock = Lock()


def _allowed(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def _set_status(key, value):
    with _lock:
        progress_status[key] = value


@allvsall_bp.route('/tools/allvsall', methods=['GET', 'POST'])
def allvsall_tool():
    """Render the allvsall tool page or handle file uploads."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file part provided."})

        file = request.files['file']
        safe_name = secure_filename(file.filename or "")
        if not safe_name:
            return jsonify({"status": "error", "message": "No file selected."})
        if not _allowed(safe_name):
            return jsonify({"status": "error", "message": "Unsupported file type."})

        file_path = os.path.join(UPLOAD_FOLDER, safe_name)
        file.save(file_path)

        _set_status(safe_name, "Initializing computation...")
        thread = threading.Thread(
            target=compute_allvsalls, args=(safe_name, file_path, CACHE_FOLDER), daemon=True
        )
        thread.start()

        return jsonify({
            "status": "success",
            "message": "File uploaded and processing started.",
            "filename": safe_name,
        })

    return render_template('allvsall.html', active_tool="allvsall")


@allvsall_bp.route('/allvsall_status/<path:filename>', methods=['GET'])
def allvsall_status(filename):
    """Get the status of the allvsall computation."""
    with _lock:
        status = progress_status.get(filename)
    if status is None:
        return jsonify({"status": "error", "message": "No process found for this file."})
    return jsonify({"status": "success", "message": status})


@allvsall_bp.route('/allvsall_data/<path:filename>', methods=['GET'])
def get_allvsall_data(filename):
    """Fetch precomputed allvsall and graph data."""
    try:
        with _lock:
            result = precomputed_results.get(filename)

        if result is None:
            return jsonify({"status": "error", "message": "Data not found for this file."})
        if "error" in result:
            return jsonify({"status": "error", "message": result["error"]})

        graph = result["graph"]
        graph_nodes = list(result["graph_nodes"])
        df = result["all_vs_all_df"]
        pos = {node: [float(x), float(y)] for node, (x, y) in result["pos"].items()}

        # Cluster id per node = connected component of the co-cluster matrix.
        _, labels = connected_components(csr_matrix(df.to_numpy() > 0), directed=False)
        node_cluster = {node: int(labels[i]) for i, node in enumerate(graph_nodes)}
        degree = {n: int(graph.degree(n)) for n in graph_nodes}

        edges = [
            {"source": u, "target": v, "weight": round(float(d.get("weight", 1.0)), 3)}
            for u, v, d in graph.edges(data=True)
        ]

        return jsonify({
            "status": "success",
            "nodes": graph_nodes,
            "node_cluster": node_cluster,
            "degree": degree,
            "edges": edges,
            "matrix": df.values.tolist(),
            "positions": pos,
            "metrics": result.get("metrics"),
        })

    except Exception as e:
        print(f"Unexpected error in /allvsall_data: {e}")
        return jsonify({"status": "error", "message": str(e)})


def compute_allvsalls(filename, input_path, cache_dir):
    """Compute allvsalls and graphs in a background thread."""
    try:
        _set_status(filename, "Reading correlation matrix...")
        _set_status(filename, "Building domain graph and running Markov clustering...")
        graph, graph_nodes, all_vs_all_df, pos, metrics = cluster_domains(input_path, cache_dir=cache_dir)

        with _lock:
            precomputed_results[filename] = {
                "graph": graph,
                "graph_nodes": graph_nodes,
                "all_vs_all_df": all_vs_all_df,
                "pos": pos,
                "metrics": metrics,
            }
            progress_status[filename] = "Completed."
    except Exception as e:
        with _lock:
            precomputed_results[filename] = {"error": str(e)}
            progress_status[filename] = f"Error: {str(e)}"
