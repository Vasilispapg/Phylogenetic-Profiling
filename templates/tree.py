import io
import os
import threading
import uuid
import logging
from threading import Lock

from flask import Blueprint, jsonify, render_template, request
from werkzeug.utils import secure_filename
from Bio import Phylo

from tree_construction.construct_tree import compute_distance_matrix, construct_tree

# Blueprint for tree routes
tree_bp = Blueprint("tree", __name__, template_folder="templates")

UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './downloads'
CACHE_FOLDER = './cache'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

# job_id -> {"status", "result", "error", "name"}.  Keyed by an opaque uuid so
# concurrent uploads (even with the same filename) never collide.
_jobs = {}
_jobs_lock = Lock()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@tree_bp.route("/tools/tree_construct", methods=["GET"])
def tree_construct_tool():
    """Render the Tree Construction tool page."""
    return render_template("tree_construct.html", active_tool="tree_construct")


@tree_bp.route("/tools/tree_viewer", methods=["GET"])
def tree_viewer_tool():
    """Render the Tree Viewer tool page."""
    return render_template("tree_viewer.html", active_tool="tree_viewer")


# ---------------------------------------------------------------------------
# Tree traversal helpers (iterative: safe for very deep trees)
# ---------------------------------------------------------------------------
def get_max_depth(root_clade):
    """Maximum depth (root == 0) of a Bio.Phylo clade, computed iteratively."""
    max_d = 0
    stack = [(root_clade, 0)]
    while stack:
        clade, depth = stack.pop()
        children = getattr(clade, "clades", None) or []
        if not children:
            max_d = max(max_d, depth)
        else:
            for child in children:
                stack.append((child, depth + 1))
    return max_d


def convert_tree_to_d3(tree, max_depth):
    """
    Convert a Bio.Phylo tree to a nested dict for D3, iteratively. Nodes deeper
    than ``max_depth`` are pruned (rendered as leaves).
    """
    root_clade = tree.root
    root_node = {"name": root_clade.name or "Unnamed", "children": []}
    stack = [(root_clade, root_node, 0)]
    while stack:
        clade, node, depth = stack.pop()
        children = getattr(clade, "clades", None) or []
        if depth >= max_depth or not children:
            node.pop("children", None)  # leaf in the (possibly pruned) view
            continue
        for child in children:
            child_node = {"name": child.name or "Unnamed", "children": []}
            node["children"].append(child_node)
            stack.append((child, child_node, depth + 1))
    return root_node


# ---------------------------------------------------------------------------
# Tree Viewer: parse an uploaded Newick file and return D3 JSON
# ---------------------------------------------------------------------------
@tree_bp.route("/tools/tree_viewer", methods=["POST"])
def tree_viewer_endpoint():
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded."}), 400

        uploaded_file = request.files["file"]
        if not uploaded_file.filename:
            return jsonify({"status": "error", "message": "No file selected."}), 400

        file_content = uploaded_file.read().decode("utf-8", errors="replace")
        try:
            tree = Phylo.read(io.StringIO(file_content), "newick")
        except Exception:
            return jsonify({"status": "error", "message": "Could not parse Newick file."}), 400

        max_depth_tree = get_max_depth(tree.root)

        # Send the full tree; the client-side depth slider prunes the view, so
        # the user can change depth without re-uploading.
        tree_data = convert_tree_to_d3(tree, max_depth_tree)

        return jsonify({
            "status": "success",
            "tree_data": tree_data,
            "max_depth_tree": max_depth_tree,
        })
    except Exception as e:
        logging.exception("tree_viewer failed")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# Tree Construction: build a phylogenetic tree from a correlation matrix
# ---------------------------------------------------------------------------
def process_tree_generation(input_path, result_path, job_id):
    """Build the tree in a background thread, updating the job record."""
    try:
        species, lower_triangle = compute_distance_matrix(input_path)
        construct_tree(species, lower_triangle, output_path=result_path)
        with _jobs_lock:
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["result"] = result_path
    except Exception as e:
        logging.exception("Tree generation failed")
        with _jobs_lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)


@tree_bp.route("/tools/tree_construct", methods=["POST"])
def construct_tree_endpoint():
    """Start background tree construction from an uploaded correlation matrix CSV."""
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded."}), 400

        uploaded_file = request.files["file"]
        safe_name = secure_filename(uploaded_file.filename or "")
        if not safe_name:
            return jsonify({"status": "error", "message": "Invalid file name."}), 400

        job_id = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{safe_name}")
        uploaded_file.save(input_path)

        base = os.path.splitext(safe_name)[0]
        result_path = os.path.join(OUTPUT_FOLDER, f"{job_id}_{base}.nw")

        with _jobs_lock:
            _jobs[job_id] = {
                "status": "in_progress",
                "result": None,
                "error": None,
                "name": f"{base}.nw",
            }

        threading.Thread(
            target=process_tree_generation,
            args=(input_path, result_path, job_id),
            daemon=True,
        ).start()

        return jsonify({
            "status": "success",
            "message": "Tree generation started.",
            "job_id": job_id,
        }), 202
    except Exception as e:
        logging.exception("construct_tree failed")
        return jsonify({"status": "error", "message": str(e)}), 500


@tree_bp.route("/tools/tree_status", methods=["GET"])
def tree_status():
    """Check the status of a tree-generation job by its job_id."""
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"status": "error", "message": "No job_id specified."}), 400

    with _jobs_lock:
        job = _jobs.get(job_id)

    if job is None:
        return jsonify({"status": "error", "message": "Job not found."}), 404

    result = job["result"]
    return jsonify({
        "status": job["status"],
        "message": job.get("error"),
        "download_url": f"/downloads/{os.path.basename(result)}" if result else None,
        "original_filename": job.get("name"),
    })
