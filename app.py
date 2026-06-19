from flask import Flask, render_template, send_from_directory
import os

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
for _d in (UPLOAD_FOLDER, OUTPUT_FOLDER, CACHE_FOLDER):
    os.makedirs(_d, exist_ok=True)

# Cap upload size (env-overridable). Default 200 MB.
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", "200")) * 1024 * 1024


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


@app.route('/how-to')
def how_to():
    """Step-by-step guide to using PhyloFlask."""
    return render_template('help.html', active_tool="help")


@app.route('/faq')
def faq():
    """Frequently asked questions and concepts."""
    return render_template('faq.html', active_tool="faq")


# Single shared download endpoint. send_from_directory rejects path traversal.
@app.route('/downloads/<path:filename>', methods=['GET'])
def download_file(filename):
    """Download a generated result file from the downloads directory."""
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


# Tool pages (GET) and their POST handlers live in the blueprints.
app.register_blueprint(blast_bp)
app.register_blueprint(heatmap_bp)
app.register_blueprint(allvsall_bp)
app.register_blueprint(tree_bp)


if __name__ == "__main__":
    # Default 8000: on macOS port 5000 (and 7000) is taken by the AirPlay
    # Receiver (Server: AirTunes), which silently hijacks http://localhost:5000.
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
