from flask import Flask, render_template
import os
import sys
from templates.heatmap import heatmap_bp
from templates.blast import blast_bp
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


@app.route('/tools/heatmap')
def heatmap_tool():
    """Render the Heatmap analysis tool page."""
    return render_template('heatmap.html', active_tool="heatmap")


app.register_blueprint(blast_bp)
app.register_blueprint(heatmap_bp)
app.register_blueprint(tree_bp)


if __name__ == "__main__":
    app.run(debug=True)
