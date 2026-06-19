import os

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from analysis.matrix_operations import create_feature_matrix, create_correlation_matrix

# Blueprint for BLAST routes
blast_bp = Blueprint('blast', __name__, template_folder='templates')

UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './downloads'
CACHE_FOLDER = './cache'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'.blastp', '.tsv', '.tab', '.txt', '.out', '.csv'}


def _allowed(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


# Upload Route
@blast_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file uploads."""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"})
    file = request.files['file']
    safe_name = secure_filename(file.filename or "")
    if not safe_name:
        return jsonify({"status": "error", "message": "No selected file"})
    if not _allowed(safe_name):
        return jsonify({"status": "error", "message": "Unsupported file type"})

    file_path = os.path.join(UPLOAD_FOLDER, safe_name)
    try:
        file.save(file_path)
        return jsonify({"status": "success", "message": "File uploaded successfully!", "filename": safe_name})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error saving file: {str(e)}"})


# Process Route
@blast_bp.route('/process', methods=['POST'])
def process_file():
    """Process uploaded file based on analysis type."""
    data = request.json or {}
    filename = secure_filename(data.get('filename') or "")
    analysis_type = data.get('analysis_type')

    if not filename:
        return jsonify({"status": "error", "message": "No filename provided"})
    if not analysis_type:
        return jsonify({"status": "error", "message": "No analysis type provided"})

    input_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(input_path):
        return jsonify({"status": "error", "message": "File not found"})

    # Output file name (unified with the CLI naming).
    if analysis_type == "features":
        output_filename = "feature_matrix.csv"
    elif analysis_type == "correlation":
        output_filename = "correlation_matrix.csv"
    else:
        return jsonify({"status": "error", "message": "Invalid analysis type"})

    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    try:
        if analysis_type == "features":
            create_feature_matrix(input_path, output_path)
        else:
            create_correlation_matrix(input_path, output_path)

        return jsonify({
            "status": "success",
            "message": "Processing completed",
            "filename": output_filename,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"})


# Get Results
@blast_bp.route('/results', methods=['GET'])
def get_results():
    """Check that a processed result file exists."""
    filename = secure_filename(request.args.get('filename') or "")
    if not filename:
        return jsonify({"status": "error", "message": "Filename not provided"})

    result_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(result_path):
        return jsonify({"status": "error", "message": "Result file not found"})

    return jsonify({"status": "success", "filename": filename})
