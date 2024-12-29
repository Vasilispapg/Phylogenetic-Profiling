from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import os
import pandas as pd
import base64
import io
import threading
import time
from analysis.clustering_analysis import utilize_mcl_onNxN, create_dash_component
from analysis.matrix_operations import find_true_positives

# Global variables
precomputed_results = {}
progress_status = {}
thread_events = {}  # To track thread completions

# Heatmap Page Layout
def layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("All-vs-All Correlation Heatmap", className="text-center mt-4"))
        ]),
        dbc.Row([
            dbc.Col([
                html.P(
                    "Upload your correlation matrix file (CSV format) to generate All-vs-All correlation heatmaps.",
                    className="text-muted text-center"
                ),
                dcc.Upload(
                    id="upload-correlation-matrix",
                    children=dbc.Button("Upload Correlation Matrix File", color="primary", className="mt-3 text-center"),
                    multiple=False
                ),
                html.Div(id="upload-status", className="text-muted mt-2 text-center"),
            ], width=12)
        ], className="mb-4"),
        dbc.Row([
            dbc.Col([
                dbc.Button("Generate Heatmaps", id="generate-heatmaps", color="success", className="mt-3  text-center"),
                dbc.Progress(id="progress-bar", striped=True, animated=True, className="mt-3"),
                html.Div(id="processing-status", className="text-info mt-2 text-center"),
                html.Div(id="output-heatmaps", className="mt-4"),
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col(html.Div(id="error-message", className="text-danger mt-4 text-center"))
        ]),
        dcc.Interval(id="progress-interval", interval=1000, n_intervals=0),  # Poll every second
    ], fluid=True)


# Compute Heatmaps in a Separate Thread
def compute_heatmaps(filename, input_path, cache_dir, event):
    try:
        progress_status[filename] = "Initializing computation..."
        true_positives = find_true_positives(input_path)
        progress_status[filename] = "True positives computed. Starting clustering..."

        time.sleep(2)  # Simulated delay
        graph, graph_nodes, all_vs_all_df, pos = utilize_mcl_onNxN(true_positives, cache_dir=cache_dir)

        # Save results globally
        precomputed_results[filename] = {
            "graph": graph,
            "graph_nodes": graph_nodes,
            "all_vs_all_df": all_vs_all_df,
            "pos": pos,
        }
        progress_status[filename] = "Completed."
    except Exception as e:
        precomputed_results[filename] = {"error": str(e)}
        progress_status[filename] = f"Error: {str(e)}"
    finally:
        # Signal thread completion
        event.set()


def register_callbacks(app):
    @app.callback(
        [Output("upload-status", "children"),
         Output("processing-status", "children"),
         Output("output-heatmaps", "children"),
         Output("error-message", "children"),
         Output("progress-bar", "value"),
         Output("progress-bar", "label")],
        [Input("upload-correlation-matrix", "contents"),
         Input("generate-heatmaps", "n_clicks"),
         Input("progress-interval", "n_intervals")],
        [State("upload-correlation-matrix", "filename")]
    )
    def handle_interaction(contents, n_clicks, n_intervals, filename):
        ctx = callback_context

        if not ctx.triggered:
            return "", "", "", "", 0, ""

        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Handle File Upload
        if triggered_id == "upload-correlation-matrix" and contents:
            try:
                content_type, content_string = contents.split(",")
                decoded = base64.b64decode(content_string)
                df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))

                if not df.empty:
                    input_path = f"./data/{filename}"
                    os.makedirs("./data", exist_ok=True)
                    df.to_csv(input_path, index=False)
                    return f"File '{filename}' uploaded successfully.", "", "", "", 0, ""
                else:
                    return "", "", "", "Uploaded file is empty.", 0, ""

            except Exception as e:
                return "", "", "", f"Error processing the file: {str(e)}", 0, ""

        # Handle Heatmap Generation
        elif triggered_id == "generate-heatmaps":
            if not filename:
                return "", "", "", "No file uploaded. Please upload a correlation matrix file.", 0, ""

            input_path = f"./data/{filename}"
            cache_dir = "./cache/"
            os.makedirs(cache_dir, exist_ok=True)

            if filename not in thread_events:
                # Initialize event to track thread completion
                event = threading.Event()
                thread_events[filename] = event
                # Start computation in a separate thread
                threading.Thread(target=compute_heatmaps, args=(filename, input_path, cache_dir, event)).start()
                return "", "Heatmap generation started. Please wait...", "", "", 0, "Starting"

        # Progress bar update via interval
        if triggered_id == "progress-interval":
            if not filename or filename not in progress_status:
                return "", "No ongoing process.", "", "", 0, ""

            progress = progress_status[filename]
            if isinstance(progress, dict):
                progress_percent = progress.get("progress", 0)
                progress_text = progress.get("status", "")

                if progress_percent == 100:
                    # Fetch the results and create heatmaps
                    result = precomputed_results[filename]
                    if "error" in result:
                        return "", f"Error: {result['error']}", "", "", 100, "Error"

                    graph = result.get("graph")
                    graph_nodes = result.get("graph_nodes")
                    all_vs_all_df = result.get("all_vs_all_df")
                    pos = result.get("pos")

                    heatmap_layout, register_callbacks = create_dash_component(graph, graph_nodes, all_vs_all_df, pos)
                    register_callbacks(app)
                    return "", "Heatmap generation completed successfully!", heatmap_layout, "", 100, "Completed"

                return "", progress_text, "", "", progress_percent, f"{progress_percent}%"

        return "", "Processing...", "", "", 0, ""

