"""Tree viewer (parse Newick) and tree builder (background NJ/UPGMA job)."""
import io
import logging
import os
import uuid

import jobs
from Bio import Phylo
from flask import Blueprint, current_app, request

from blueprints._api import fail, ok, save_upload
from config import DOWNLOAD_DIR, UPLOAD_DIR
from tree_construction.nj import METHODS

tree_bp = Blueprint("tree", __name__)
log = logging.getLogger(__name__)

# The front-ends branch on these strings; `state` from the job store is mapped
# onto them so both stay in sync.
LEGACY_STATE = {"queued": "in_progress", "running": "in_progress",
                "done": "completed", "failed": "failed"}


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
@tree_bp.post("/newick")
def tree_viewer_endpoint():
    token = uuid.uuid4().hex
    scratch = UPLOAD_DIR / f"{token}.nw"
    name, err = save_upload(request.files.get("file"), "newick", scratch)
    if err:
        return err
    try:
        content = scratch.read_text(encoding="utf-8", errors="replace")
    finally:
        scratch.unlink(missing_ok=True)
    try:
        tree = Phylo.read(io.StringIO(content), "newick")
    except Exception:
        return fail("Could not parse Newick file.", 400)

    # Bio.Phylo's parser is lenient: arbitrary text comes back as a single
    # unnamed clade rather than an error, so check the result is really a tree.
    if "(" not in content or ";" not in content or tree.count_terminals() < 2:
        return fail("That does not look like a Newick tree "
                    "(expected nested parentheses ending in ';').", 400)

    # Send the full tree; the client-side depth slider prunes the view, so the
    # user can change depth without re-uploading.
    max_depth_tree = get_max_depth(tree.root)
    return ok(tree_data=convert_tree_to_d3(tree, max_depth_tree),
              max_depth_tree=max_depth_tree, original_filename=name)


# ---------------------------------------------------------------------------
# Tree Construction: build a phylogenetic tree from a correlation matrix
# ---------------------------------------------------------------------------
@tree_bp.post("/trees")
def construct_tree_endpoint():
    """Start a background tree build from an uploaded correlation matrix CSV."""
    method = (request.form.get("method") or "nj").lower()
    if method not in METHODS:
        return fail(f"Unknown method {method!r}; expected one of {sorted(METHODS)}.", 400)

    token = uuid.uuid4().hex
    name, err = save_upload(request.files.get("file"), "matrix", UPLOAD_DIR / token)
    if err:
        return err
    input_path = UPLOAD_DIR / f"{token}_{name}"
    (UPLOAD_DIR / token).rename(input_path)

    base = os.path.splitext(name)[0]
    result_path = DOWNLOAD_DIR / f"{token}_{base}.nw"

    from workers import run_tree_job
    job_id = current_app.submit_job(
        "tree", run_tree_job, str(input_path), str(result_path), f"{base}.nw", method,
        message="Queued for tree construction...",
    )
    return ok(message="Tree generation started.", job_id=job_id), 202


@tree_bp.get("/trees/<job_id>")
def tree_status(job_id):
    """Check the status of a tree-generation job."""
    job = jobs.get(job_id)
    if job is None or job["kind"] != "tree":
        return fail("No tree job with that id.", 404)

    result = job["result"] or {}
    download = result.get("download")
    return ok_status(job, download)


def ok_status(job, download):
    from flask import jsonify
    return jsonify({
        # Legacy field the front-ends branch on.
        "status": LEGACY_STATE[job["state"]],
        "state": job["state"],
        "progress": job["progress"],
        "message": job["error"] or job["message"],
        "download_url": f"/api/downloads/{download}" if download else None,
        "original_filename": (job["result"] or {}).get("name"),
    })
