from flask import Blueprint, jsonify, render_template, request
import os
import threading
import sys
from threading import Lock

# Include project root for analysis scripts
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from analysis.clustering_analysis import utilize_mcl_onNxN
from analysis.matrix_operations import find_true_positives

# Blueprint for heatmap routes
heatmap_bp = Blueprint('heatmap', __name__, template_folder='templates')

UPLOAD_FOLDER = './uploads'
CACHE_FOLDER = './cache'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

# Global variables
precomputed_results = {}
progress_status = {}
precomputed_results_lock = Lock()

@heatmap_bp.route('/tools/heatmap', methods=['GET', 'POST'])
def heatmap_tool():
    """Render the Heatmap tool page or handle file uploads."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file part provided."})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "No file selected."})

        # Save uploaded file
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # Start computation in background
        event = threading.Event()
        thread = threading.Thread(target=compute_heatmaps, args=(file.filename, file_path, CACHE_FOLDER, event))
        thread.start()

        return jsonify({"status": "success", "message": "File uploaded and processing started.", "filename": file.filename})

    return render_template('heatmap.html', active_tool="heatmap")


@heatmap_bp.route('/heatmap_status/<filename>', methods=['GET'])
def heatmap_status(filename):
    """Get the status of the heatmap computation."""
    if filename not in progress_status:
        return jsonify({"status": "error", "message": "No process found for this file."})

    return jsonify({"status": "success", "message": progress_status[filename]})


@heatmap_bp.route('/heatmap_data/<filename>', methods=['GET'])
def get_heatmap_data(filename):
    """Fetch precomputed heatmap and graph data."""
    try:
        print(f"Request received for heatmap data: {filename}")

        if filename not in precomputed_results:
            print(f"Error: Data not found for {filename}")
            return jsonify({"status": "error", "message": "Data not found for this file."})

        result = precomputed_results[filename]
        if "error" in result:
            print(f"Error in precomputed results: {result['error']}")
            return jsonify({"status": "error", "message": result["error"]})

        graph = result["graph"]
        graph_nodes = list(result["graph_nodes"])
        all_vs_all_df = result["all_vs_all_df"].values.tolist()  # Convert DataFrame to list of lists
        pos = {node: [float(x), float(y)] for node, (x, y) in result["pos"].items()}

        # Log the data being returned
        print(f"Graph Nodes (sample): {graph_nodes[:5]}")
        print(f"Graph Edges (sample): {list(graph.edges())[:5]}")
        print(f"Positions (sample): {list(pos.items())[:5]}")

        return jsonify({
            "status": "success",
            "nodes": graph_nodes,
            "edges": [{"source": u, "target": v} for u, v in graph.edges()],
            "matrix": all_vs_all_df,
            "positions": pos
        })

    except Exception as e:
        print(f"Unexpected error in /heatmap_data: {e}")
        return jsonify({"status": "error", "message": str(e)})




def compute_heatmaps(filename, input_path, cache_dir, event):
    """Compute heatmaps and graphs in a background thread."""
    try:
        progress_status[filename] = "Initializing computation..."
        true_positives = find_true_positives(input_path)

        progress_status[filename] = "Performing clustering..."
        graph, graph_nodes, all_vs_all_df, pos = utilize_mcl_onNxN(true_positives, cache_dir=cache_dir)

        with precomputed_results_lock:
            precomputed_results[filename] = {
                "graph": graph,
                "graph_nodes": graph_nodes,
                "all_vs_all_df": all_vs_all_df,
                "pos": pos,
            }

        progress_status[filename] = "Completed."
    except Exception as e:
        with precomputed_results_lock:
            precomputed_results[filename] = {"error": str(e)}
        progress_status[filename] = f"Error: {str(e)}"
    finally:
        event.set()
