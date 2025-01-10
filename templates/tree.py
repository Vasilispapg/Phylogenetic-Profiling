from flask import Blueprint, jsonify, render_template, request
import os
import threading
from threading import Lock
from tree_construction.construct_tree import load_species_data, approximate_distance_matrix, construct_tree
from Bio import Phylo
import io
import sys

# Blueprint for tree routes
tree_bp = Blueprint("tree", __name__, template_folder="templates")

UPLOAD_FOLDER = "./uploads"
CACHE_FOLDER = "./cache"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

# Global variables
precomputed_results = {}
progress_status = {}
precomputed_results_lock = Lock()


# Render Tree Construct Page
@tree_bp.route("/tools/tree_construct", methods=["GET"])
def tree_construct_tool():
    """Render the Tree Construction tool page."""
    return render_template("tree_construct.html", active_tool="tree_construct")


# Render Tree Viewer Page
@tree_bp.route("/tools/tree_viewer", methods=["GET"])
def tree_viewer_tool():
    """Render the Tree Viewer tool page."""
    return render_template("tree_viewer.html", active_tool="tree_viewer")


# Endpoint for Tree Construction
@tree_bp.route("/tools/tree_construct", methods=["POST"])
def construct_tree_endpoint():
    """Endpoint for tree construction."""
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded."}), 400

        uploaded_file = request.files["file"]
        file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        uploaded_file.save(file_path)

        # Get max depth (optional)
        max_depth = int(request.form.get("max_depth", 12))

        # Start tree generation in a separate thread
        result_filename = os.path.join(CACHE_FOLDER, f"{os.path.splitext(uploaded_file.filename)[0]}_tree.nw")
        threading.Thread(target=process_tree_generation, args=(file_path, result_filename)).start()

        return jsonify({"status": "success", "message": "Tree generation started.", "result_file": result_filename}), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@tree_bp.route("/tools/tree_viewer", methods=["POST"])
def tree_viewer_endpoint():
    try:
        # Ensure a file is uploaded
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded."}), 400

        # Read the uploaded file
        uploaded_file = request.files["file"]
        file_content = uploaded_file.read().decode("utf-8")  # Ensure text mode

        # Parse the Newick file
        tree = Phylo.read(io.StringIO(file_content), "newick")
        print(tree)  # Debug parsed tree
        print(tree.root)  # Debug root node

        # Get max depth for processing
        max_depth = int(request.form.get("max_depth", 12))

        # Convert the tree to D3.js-compatible JSON
        tree_data = convert_tree_to_d3(tree, max_depth)

        # Return JSON data
        return jsonify({"status": "success", "tree_data": tree_data})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



def convert_tree_to_d3(tree, max_depth):
    def traverse(clade, depth=0):
        if depth > max_depth or not hasattr(clade, "clades"):
            return {"name": clade.name or "Unnamed"}
        return {
            "name": clade.name or "Unnamed",
            "children": [traverse(subclade, depth + 1) for subclade in clade.clades]
        }

    # Access the root node explicitly
    if hasattr(tree, "root"):
        return traverse(tree.root)
    else:
        raise ValueError("Tree does not have a root attribute.")



def process_tree_generation(input_file, result_file):
    """Generate the tree in a separate thread."""
    try:
        # Load species data
        species_data = load_species_data(input_file)

        # Approximate the distance matrix
        distance_matrix = approximate_distance_matrix(species_data)

        # Construct the tree and save it to the result file
        construct_tree(distance_matrix, output_file=result_file)

        # Update progress
        with precomputed_results_lock:
            precomputed_results[input_file] = result_file
            progress_status[input_file] = "completed"
    except Exception as e:
        print(f"Error in tree generation: {e}")
        with precomputed_results_lock:
            progress_status[input_file] = "failed"
