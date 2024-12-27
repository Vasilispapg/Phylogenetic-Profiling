# display_correlation.py
import plotly.graph_objects as go
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import pandas as pd
import plotly.graph_objects as go

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
    Display a species × domains heatmap with an interactive dropdown for feature selection and a loading animation.

    Parameters:
    - correlation_matrix_path (str): Path to the CSV file containing the species × domains JSON feature matrix.
    """
    try:
        # Load the JSON feature matrix
        feature_matrix = pd.read_csv(correlation_matrix_path, index_col=0)

        # Extract all available feature keys from the JSON-like data
        first_cell = next(iter(feature_matrix.iloc[0].dropna()), "{}")
        available_features = list(eval(first_cell).keys())

        # Initialize the Dash app
        app = Dash(__name__)

        # Define the app layout
        app.layout = html.Div([
            html.H1("Interactive Species × Domains Heatmap"),
            html.Label("Select Feature:"),
            dcc.Dropdown(
                id="feature-dropdown",
                options=[{"label": feature, "value": feature} for feature in available_features],
                value=available_features[0],  # Default selection
                clearable=False
            ),
            dcc.Loading(
                id="loading-animation",
                type="circle",  # Options: "circle", "dot", "default"
                children=[
                    dcc.Graph(id="heatmap")
                ],
                fullscreen=False  # Set to True for a full-screen loading animation
            ),
        ])

        # Define callback to update heatmap based on selected feature
        @app.callback(
            Output("heatmap", "figure"),
            Input("feature-dropdown", "value")
        )
        def update_heatmap(selected_feature):
            # Extract data for the selected feature
            feature_data = feature_matrix.applymap(
                lambda cell: eval(cell).get(selected_feature) if cell != '{}' else 0
            )

            # Generate hover information with neatly formatted JSON details
            hover_text = []
            for i, species in enumerate(feature_matrix.index):
                hover_row = []
                for j, domain in enumerate(feature_matrix.columns):
                    json_data = eval(feature_matrix.iat[i, j])
                    if json_data:  # If the cell contains valid data
                        pretty_features = "<br>".join(
                            f"<b>{key}:</b> {value}" for key, value in json_data.items()
                        )
                    else:
                        pretty_features = "No Data"
                    hover_info = (
                        f"<b>Species:</b> {species}<br>"
                        f"<b>Domain:</b> {domain}<br>"
                        f"{pretty_features}"
                    )
                    hover_row.append(hover_info)
                hover_text.append(hover_row)

            # Define the heatmap
            heatmap_trace = go.Heatmap(
                z=feature_data.values,
                x=feature_matrix.columns,
                y=feature_matrix.index,
                colorscale='hot',
                colorbar=dict(title=selected_feature),
                hoverinfo="text",
                text=hover_text
            )

            # Create the Plotly figure
            fig = go.Figure(data=[heatmap_trace])

            # Configure layout
            fig.update_layout(
                title=f"Species × Domains Heatmap ({selected_feature})",
                xaxis=dict(title="Domains"),
                yaxis=dict(title="Species"),
                height=1080,
                width=1600,
            )

            return fig

        # Run the app
        app.run_server(debug=True)

    except Exception as e:
        print(f"An error occurred: {e}")

    """
    Display a species × domains heatmap with an interactive dropdown for feature selection.

    Parameters:
    - correlation_matrix_path (str): Path to the CSV file containing the species × domains JSON feature matrix.
    """
    try:
        # Load the JSON feature matrix
        feature_matrix = pd.read_csv(correlation_matrix_path, index_col=0)

        # Extract all available feature keys from the JSON-like data
        first_cell = next(iter(feature_matrix.iloc[0].dropna()), "{}")
        available_features = list(eval(first_cell).keys())

        # Initialize the Dash app
        app = Dash(__name__)

        # Define the app layout
        app.layout = html.Div([
            html.H1("Interactive Species × Domains Heatmap"),
            html.Label("Select Feature:"),
            dcc.Dropdown(
                id="feature-dropdown",
                options=[{"label": feature, "value": feature} for feature in available_features],
                value=available_features[0],  # Default selection
                clearable=False
            ),
            dcc.Graph(id="heatmap"),
        ])

        # Define callback to update heatmap based on selected feature
        @app.callback(
            Output("heatmap", "figure"),
            Input("feature-dropdown", "value")
        )
        def update_heatmap(selected_feature):
            # Extract data for the selected feature
            feature_data = feature_matrix.applymap(
                lambda cell: eval(cell).get(selected_feature) if cell != '{}' else 0
            )

            # Generate hover information with neatly formatted JSON details
            hover_text = []
            for i, species in enumerate(feature_matrix.index):
                hover_row = []
                for j, domain in enumerate(feature_matrix.columns):
                    json_data = eval(feature_matrix.iat[i, j])
                    if json_data:  # If the cell contains valid data
                        pretty_features = "<br>".join(
                            f"<b>{key}:</b> {value}" for key, value in json_data.items()
                        )
                    else:
                        pretty_features = "No Data"
                    hover_info = (
                        f"<b>Species:</b> {species}<br>"
                        f"<b>Domain:</b> {domain}<br>"
                        f"{pretty_features}"
                    )
                    hover_row.append(hover_info)
                hover_text.append(hover_row)

            # Define the heatmap
            heatmap_trace = go.Heatmap(
                z=feature_data.values,
                x=feature_matrix.columns,
                y=feature_matrix.index,
                colorscale='Viridis',
                colorbar=dict(title=selected_feature),
                hoverinfo="text",
                text=hover_text
            )

            # Create the Plotly figure
            fig = go.Figure(data=[heatmap_trace])

            # Configure layout
            fig.update_layout(
                title=f"Species × Domains Heatmap ({selected_feature})",
                xaxis=dict(title="Domains"),
                yaxis=dict(title="Species"),
                height=800,
                width=1200
            )

            return fig

        # Run the app
        app.run_server(debug=True)

    except Exception as e:
        print(f"An error occurred: {e}")