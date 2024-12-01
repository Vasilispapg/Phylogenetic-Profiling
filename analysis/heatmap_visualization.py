import pandas as pd
from dash import Dash, dcc, html
import plotly.graph_objects as go
import plotly.express as px


def create_species_domain_heatmap(matrix):
    """
    Create a heatmap with species as rows and domains as columns.
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


def run_heatmap_app(matrix):
    """
    Run a Dash app to display the interactive heatmap.
    """
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1("Species-Domain Heatmap"),
        dcc.Graph(
            id="heatmap",
            figure=create_species_domain_heatmap(matrix)
        )
    ])

    app.run_server(debug=True)
