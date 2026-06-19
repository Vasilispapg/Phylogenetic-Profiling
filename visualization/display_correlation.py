# display_correlation.py
import json
import os

import plotly.graph_objects as go
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import numpy as np


def _dash_debug():
    return os.environ.get("DASH_DEBUG", "").lower() in ("1", "true", "yes")


def _parse_cell(cell):
    """Safely parse a JSON feature-vector cell into a dict (never eval)."""
    if not isinstance(cell, str) or cell in ("", "{}"):
        return {}
    try:
        return json.loads(cell)
    except (ValueError, TypeError):
        return {}

def display_species_domain_heatmap(correlation_matrix_path="species_domain_count_matrix.csv"):
    """
    Display a species × domains count heatmap without dendrograms.

    Parameters:
    - correlation_matrix_path (str): Path to the CSV file containing the species × domains count matrix.
    """
    # Load the count matrix
    count_matrix = pd.read_csv(correlation_matrix_path, index_col=0)

    # Create detailed hover information for each cell in the heatmap
    hover_text = []
    for i, species in enumerate(count_matrix.index):
        hover_row = []
        for j, domain in enumerate(count_matrix.columns):
            hover_row.append(f"<b>Species:</b> {species}<br><b>Domain:</b> {domain}<br><b>Count:</b> {count_matrix.iat[i, j]}")
        hover_text.append(hover_row)

    # Define a biologically relevant colorscale
    heatmap_trace = go.Heatmap(
        z=count_matrix.values,
        x=count_matrix.columns,
        y=count_matrix.index,
        colorscale='hot',  # Vibrant colors for clear visibility
        colorbar=dict(title='Count'),
        hoverinfo="text",
        text=hover_text  # Detailed hover info for each cell
    )

    # Create Plotly figure
    fig = go.Figure()

    # Add the heatmap trace
    fig.add_trace(heatmap_trace)

    # Configure layout
    fig.update_layout(
        title="Species × Domains Count Matrix",
        xaxis=dict(title="Domains"),
        yaxis=dict(title="Species"),
        height=1080,
        width=1600,
        annotations=[
            dict(
                text="Heatmap Analysis",
                xref="paper", yref="paper",
                x=0.5, y=1.1, showarrow=False,
                font=dict(size=16)
            )
        ]
    )

    # Display the figure
    fig.show()

def display_species_domain_heatmap_with_features(correlation_matrix_path="species_domain_count_matrix.csv"):
    """
    Display a species × domains heatmap with live filters, sorting, and animations.

    Parameters:
    - correlation_matrix_path (str): Path to the CSV file containing the species × domains JSON feature matrix.
    """
    try:
        # Load the JSON feature matrix
        feature_matrix = pd.read_csv(correlation_matrix_path, index_col=0)

        # Extract all available feature keys from the first non-empty cell.
        available_features = []
        for cell in feature_matrix.to_numpy().ravel():
            parsed = _parse_cell(cell)
            if parsed:
                available_features = list(parsed.keys())
                break
        if not available_features:
            raise ValueError("No feature data found in the matrix.")

        # Initialize the Dash app
        app = Dash(__name__)

        # Define the app layout
        app.layout = html.Div([
            html.H1("Interactive Species × Domains Heatmap", style={"textAlign": "center"}),

            html.Label("Select Feature:"),
            dcc.Dropdown(
                id="feature-dropdown",
                options=[{"label": feature, "value": feature} for feature in available_features],
                value=available_features[0],
                clearable=False
            ),

            html.Label("Minimum Hits (Filter):"),
            dcc.Slider(
                id="num-hits-slider",
                min=0,
                max=10,
                step=1,
                marks={i: str(i) for i in range(11)},
                value=0,
            ),

            html.Label("Sort Data:"),
            dcc.RadioItems(
                id="sort-radio",
                options=[
                    {"label": "Ascending", "value": "asc"},
                    {"label": "Descending", "value": "desc"}
                ],
                value="desc",
                inline=True
            ),

            dcc.Graph(id="interactive-heatmap"),
        ])

        # Callback to update heatmap based on filters, sorting, and feature selection
        @app.callback(
            Output("interactive-heatmap", "figure"),
            Input("feature-dropdown", "value"),
            Input("num-hits-slider", "value"),
            Input("sort-radio", "value")
        )
        def update_heatmap(selected_feature, min_hits, sort_order):
            # Extract data for the selected feature
            feature_data = feature_matrix.map(
                lambda cell: _parse_cell(cell).get(selected_feature, 0) or 0
            )

            # Filter data based on minimum hits
            num_hits_data = feature_matrix.map(
                lambda cell: _parse_cell(cell).get("num_hits", 0) or 0
            )
            mask = num_hits_data >= min_hits
            feature_data_filtered = feature_data.where(mask, other=0)

            # Apply logarithmic scaling
            feature_data_log = feature_data_filtered.map(lambda x: np.log1p(x) / np.log(20) if x > 0 else 0)

            # Sort the data
            if sort_order == "asc":
                feature_data_sorted = feature_data_log.sort_index(axis=0).sort_index(axis=1)
            else:
                feature_data_sorted = feature_data_log.sort_index(axis=0, ascending=False).sort_index(axis=1, ascending=False)

            # Generate hover information
            hover_text = []
            for i, species in enumerate(feature_matrix.index):
                hover_row = []
                for j, domain in enumerate(feature_matrix.columns):
                    json_data = _parse_cell(feature_matrix.iat[i, j])
                    hover_info = f"<b>Species:</b> {species}<br><b>Domain:</b> {domain}"
                    hover_info += "".join(f"<br><b>{k}:</b> {v}" for k, v in json_data.items())
                    hover_row.append(hover_info)
                hover_text.append(hover_row)

            # Create the heatmap
            heatmap_trace = go.Heatmap(
                z=feature_data_sorted.values,
                x=feature_data_sorted.columns,
                y=feature_data_sorted.index,
                colorscale="Inferno",
                colorbar=dict(title=selected_feature),
                hoverinfo="text",
                text=hover_text
            )

            # Create the figure with smooth transitions
            fig = go.Figure(data=[heatmap_trace])
            fig.update_layout(
                title=f"Species × Domains Heatmap ({selected_feature}) - Filter: Hits ≥ {min_hits}",
                xaxis=dict(title="Domains"),
                yaxis=dict(title="Species"),
                height=1080,
                width=1600,
                transition={"duration": 500}  # Smooth transition
            )
            return fig

        # Run the app
        app.run(debug=_dash_debug())

    except Exception as e:
        print(f"An error occurred: {e}")