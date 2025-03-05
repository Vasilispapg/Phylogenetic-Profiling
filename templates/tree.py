from flask import Blueprint, jsonify, render_template, request,send_file
import os
import threading
from threading import Lock
from tree_construction.construct_tree import load_species_data, approximate_distance_matrix, construct_tree
from Bio import Phylo
import io
import sys
import uuid
import logging

# Blueprint for tree routes
tree_bp = Blueprint("tree", __name__, template_folder="templates")

UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './downloads'
CACHE_FOLDER = './cache'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

# Global variables
precomputed_results = {}
progress_status = {}
precomputed_results_lock = Lock()
uploaded_files_mapping = {}


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

def get_max_depth(clade, current_depth=0):
    """Recursively calculate the maximum depth of the tree."""
    if not clade.clades:  # If it's a leaf node
        return current_depth
    return max(get_max_depth(child, current_depth + 1) for child in clade.clades)


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

        # Get max depth for processing
        max_depth = int(request.form.get("max_depth", 12))
        max_depth = max(max_depth, 1000000000000000) # Arbitrary large number

        # Convert the tree to D3.js-compatible JSON
        tree_data = convert_tree_to_d3(tree, max_depth)
        
        max_depth_tree = get_max_depth(tree.root)


        # Return JSON data
        return jsonify({"status": "success", "tree_data": tree_data,"max_depth_tree":max_depth_tree})
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
        with precomputed_results_lock:
            progress_status[input_file] = "in_progress"
            
        species_data = load_species_data(input_file)

        # Approximate the distance matrix
        representative_species, lower_triangle_matrix = approximate_distance_matrix(species_data)

        # Construct the tree and save it to the result file
        construct_tree(representative_species, lower_triangle_matrix, output_path=result_file)

        # Update progress
        with precomputed_results_lock:
            precomputed_results[input_file] = result_file
            progress_status[input_file] = "completed"
    except Exception as e:
        print(f"Error in tree generation: {e}")
        with precomputed_results_lock:
            progress_status[input_file] = "failed"
            
            

@tree_bp.route("/tools/tree_status", methods=["GET"])
def tree_status():
    """Check the status of tree generation."""
    original_filename = request.args.get("input_file")
    if not original_filename:
        return jsonify({"status": "error", "message": "No input file specified."}), 400

    # Look up the unique filename using the original filename
    logging.info(uploaded_files_mapping)
    unique_filename = uploaded_files_mapping.get(original_filename)
    if not unique_filename:
        return jsonify({"status": "error", "message": "File not found."}), 404

    with precomputed_results_lock:
        status = progress_status.get(unique_filename, "not_found")
        result_file = precomputed_results.get(unique_filename)

    return jsonify({
        "status": status,
        "download_url": f"/downloads/{os.path.basename(result_file)}" if result_file else None,
        "original_filename": original_filename
    })


@tree_bp.route('/downloads/<filename>', methods=['GET'])
def download_tree(filename):
    """Download the constructed tree file."""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404

    return send_file(file_path, as_attachment=True)


@tree_bp.route("/tools/tree_construct", methods=["POST"])
def construct_tree_endpoint():
    """Endpoint for tree construction."""
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded."}), 400

        uploaded_file = request.files["file"]
        original_filename = uploaded_file.filename
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        logging.info(file_path)
        # rename the uplaoded_file to unique_filename
        uploaded_file.save(file_path)
        

        # Map the original filename to the unique filename
        uploaded_files_mapping[original_filename] = unique_filename   
        logging.info(uploaded_files_mapping)
        logging.info(uploaded_files_mapping.get(original_filename))    

        # Output filename with .nw extension
        result_filename = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(original_filename)[0]}.nw")

        # Start tree generation in a separate thread
        threading.Thread(target=process_tree_generation, args=(file_path, result_filename)).start()

        return jsonify({
            "status": "success",
            "message": "Tree generation started.",
            "download_url": f"/downloads/{os.path.basename(result_filename)}",
            "original_filename": os.path.basename(result_filename)
        }), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
