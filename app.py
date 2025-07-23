from flask import Flask, render_template
import os
import sys
from templates.allvsall import allvsall_bp
from templates.blast import blast_bp
from templates.heatmap import heatmap_bp
from templates.tree import tree_bp

# Initialize Flask app
app = Flask(__name__, template_folder="pages", static_folder="public")

# Directories
UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './downloads'
CACHE_FOLDER = './cache'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

# Global variables
precomputed_results = {}
progress_status = {}

# Main Page
@app.route('/')
def index():
    """Main page with navigation."""
    return render_template('index.html', active_tool="index")

@app.route('/tools')
@app.route('/tools/blast')
def blast_tool():
    """Render the BLAST analysis tool page (default)."""
    return render_template('blast.html', active_tool="blast")


@app.route('/tools/allvsall')
def allvsall_tool():
    """Render the allvsall analysis tool page."""
    return render_template('allvsall.html', active_tool="allvsall")

@app.route('/tools/heatmap')
def heatmap_tool():
    """Render the allvsall analysis tool page."""
    return render_template('heatmap.html', active_tool="heatmap")


app.register_blueprint(blast_bp)
app.register_blueprint(heatmap_bp)
app.register_blueprint(allvsall_bp)
app.register_blueprint(tree_bp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

