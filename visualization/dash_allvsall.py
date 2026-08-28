"""
Standalone Dash explorer for the domain network (CLI only: ``main.py --all_vs_all``).

Kept out of ``analysis/`` so that importing the clustering code -- which every web
blueprint does -- never pulls Dash and Plotly into the web process.
"""
import os

import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html


def _dash_debug():
    """Dash debug mode is off unless explicitly enabled via env var."""
    return os.environ.get("DASH_DEBUG", "").lower() in ("1", "true", "yes")


def create_dash_app(graph, nodes, all_vs_all_df, pos):
    """Dash app showing the co-cluster heatmap next to the domain graph."""
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1("Markov Clustering Visualization",
                style={"textAlign": "center", "marginBottom": "30px"}),
        html.Div([
            dcc.Dropdown(
                id="domain-selector",
                options=[{"label": node, "value": node} for node in nodes],
                placeholder="Select one or more domains...",
                multi=True,
                style={"width": "50%", "margin": "auto"},
            ),
        ], style={"marginBottom": "20px", "textAlign": "center"}),
        dcc.Loading(id="loading", type="circle", children=[
            html.Div(dcc.Graph(id="heatmap", style={"width": "100%", "display": "block"}),
                     style={"marginBottom": "50px"}),
            html.Div(dcc.Graph(id="graph", style={"width": "100%", "display": "block"})),
        ]),
    ])

    @app.callback(
        [Output("heatmap", "figure"), Output("graph", "figure")],
        [Input("domain-selector", "value")],
    )
    def update_graphs(selected_domains):
        selected_domains = selected_domains or []
        if selected_domains:
            filtered_edges = [
                (u, v) for u, v in graph.edges()
                if u in selected_domains or v in selected_domains
            ]
            filtered_nodes = list({node for edge in filtered_edges for node in edge})
            filtered_matrix = all_vs_all_df.loc[filtered_nodes, filtered_nodes]
        else:
            filtered_nodes = nodes
            filtered_edges = list(graph.edges())
            filtered_matrix = all_vs_all_df

        if filtered_matrix.empty or not filtered_nodes:
            empty = go.Figure()
            empty.update_layout(title="No Data Available")
            return px.imshow([[0]], title="No Data Available"), empty

        heatmap_fig = px.imshow(
            filtered_matrix, x=filtered_nodes, y=filtered_nodes,
            color_continuous_scale="Viridis",
            labels={"x": "Nodes", "y": "Nodes", "color": "Similarity"},
            title="All-vs-All Clustering Matrix",
        )
        heatmap_fig.update_layout(
            autosize=True, height=1200, margin=dict(l=50, r=50, t=100, b=50),
            xaxis=dict(tickangle=45, automargin=True), yaxis=dict(automargin=True),
            coloraxis_colorbar=dict(title="Cluster Similarity", len=0.75),
        )

        edge_x, edge_y = [], []
        for source, target in filtered_edges:
            x0, y0 = pos[source]
            x1, y1 = pos[target]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        graph_fig = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color="red"),
                       hoverinfo="none", mode="lines"),
            go.Scatter(
                x=[pos[n][0] for n in filtered_nodes],
                y=[pos[n][1] for n in filtered_nodes],
                mode="markers+text",
                marker=dict(size=12, showscale=False, color=[
                    "rgba(255,100,100,0.8)" if n in selected_domains else "rgba(100,100,255,0.5)"
                    for n in filtered_nodes
                ]),
                text=list(filtered_nodes), textposition="top center", hoverinfo="text",
            ),
        ])
        graph_fig.update_layout(
            title="Graph Visualization with Selected Nodes and Neighbors",
            height=1200, showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False),
            margin=dict(l=50, r=50, t=100, b=50),
        )
        return heatmap_fig, graph_fig

    app.run = _wrap_run(app)
    return app


def _wrap_run(app):
    original = app.run

    def run(*args, **kwargs):
        kwargs.setdefault("debug", _dash_debug())
        return original(*args, **kwargs)
    return run
