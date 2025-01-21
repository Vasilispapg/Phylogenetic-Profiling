from flask import Blueprint, jsonify, render_template, request
import os
import sys
import json
import pandas as pd
import uuid
from threading import Lock

# Include project root for analysis scripts
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

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

@heatmap_bp.route('/tools/heatmap', methods=['GET'])
def heatmap_tool():
    # Render the page with no file-upload POST handling
    return render_template('heatmap.html', active_tool="heatmap")


@heatmap_bp.route('/tools/heatmap_tabs', methods=['GET'])
def heatmap_tabs():
    return render_template('heatmap_tabs.html')