import plotly.graph_objects as go
from dash import Dash, dcc, html
import pdb
from analyze_genomes import create_correlation_matrix


def create_species_domain_heatmap(matrix):
    """
    Create a heatmap with species as rows and domains as columns.

    Parameters:
    - matrix (pd.DataFrame): The matrix with species as rows and domains as columns.

    Returns:
    - go.Figure: A Plotly figure object containing the heatmap.
    """
    
    heatmap = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            x=matrix.columns,
            y=matrix.index,
            colorscale="Viridis",
            colorbar={"title": "Percent Identity"}
        )
    )
    heatmap.update_layout(
        title="Species-Domain Heatmap",
        xaxis_title="Domains",
        yaxis_title="Species",
        height=800,
        width=1200,
    )
    return heatmap

def run_heatmap_app(blast_file_path):
    """
    Run a Dash app to display the interactive heatmap.

    Parameters:
    - blast_file_path (str): Path to the BLAST file.
    """
    # Parse the BLAST file to create the matrix
    matrix = create_correlation_matrix(blast_file_path)

    # Initialize the Dash app
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1("Species-Domain Heatmap"),
        dcc.Graph(
            id="heatmap",
            figure=create_species_domain_heatmap(matrix)
        )
    ])

    # Run the Dash app
    app.run_server(debug=True)
