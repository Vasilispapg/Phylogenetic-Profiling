import os

from flask import Blueprint, render_template

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
