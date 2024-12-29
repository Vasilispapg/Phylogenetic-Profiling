from flask import Blueprint, jsonify, request,send_file
import os
import sys
# Include project root for analysis scripts
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from analysis.matrix_operations import create_feature_matrix, create_correlation_matrix

# Blueprint for heatmap routes
blast_bp = Blueprint('blast', __name__, template_folder='templates')

UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './downloads'
CACHE_FOLDER = './cache'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

# Upload Route
@blast_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file uploads."""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"})

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    try:
        file.save(file_path)
        return jsonify({"status": "success", "message": "File uploaded successfully!", "filename": file.filename})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error saving file: {str(e)}"})

# Process Route
@blast_bp.route('/process', methods=['POST'])
def process_file():
    """Process uploaded file based on analysis type."""
    data = request.json
    filename = data.get('filename')
    analysis_type = data.get('analysis_type')

    if not filename:
        return jsonify({"status": "error", "message": "No filename provided"})
    if not analysis_type:
        return jsonify({"status": "error", "message": "No analysis type provided"})

    input_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(input_path):
        return jsonify({"status": "error", "message": "File not found"})

    # Determine output file name based on analysis type
    if analysis_type == "features":
        output_filename = "feature_result.csv"
    elif analysis_type == "correlation":
        output_filename = "correlation_matrix.csv"
    else:
        return jsonify({"status": "error", "message": "Invalid analysis type"})

    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    try:
        if analysis_type == "features":
            create_feature_matrix(input_path, output_path)
        elif analysis_type == "correlation":
            create_correlation_matrix(input_path, output_path)

        return jsonify({"status": "success", "message": "Processing completed", "output_path": output_path})
    except Exception as e:
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"})

# Get Results
@blast_bp.route('/results', methods=['GET'])
def get_results():
    """Fetch results for the processed file."""
    filename = request.args.get('filename')
    if not filename:
        return jsonify({"status": "error", "message": "Filename not provided"})

    result_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(result_path):
        return jsonify({"status": "error", "message": "Result file not found"})

    return jsonify({"status": "success", "file_path": result_path})

# Download Results
@blast_bp.route('/downloads/<filename>', methods=['GET'])
def download_file(filename):
    """Download processed file."""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404

    return send_file(file_path, as_attachment=True)