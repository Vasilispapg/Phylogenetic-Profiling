import time
import markov_clustering as mc
import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import plotly.express as px
import joblib
import os
import dash_bootstrap_components as dbc


def prepare_clustering(true_positives):
    """
    Prepares clustering and visualization data.
    """
    # Step 1: Create a graph
    graph = nx.Graph()
    graph.add_edges_from(true_positives)

    # Convert graph to sparse adjacency matrix
    adj_matrix = nx.to_scipy_sparse_array(graph, weight=None)
    adj_matrix = csr_matrix(adj_matrix)

    # Run MCL
    mcl_start = time.time()
    result = mc.run_mcl(adj_matrix, inflation=1.5)
    clusters = mc.get_clusters(result)
    print(f"MCL Execution Time: {time.time() - mcl_start:.2f} seconds")

    # Rebuild all-vs-all matrix
    nodes = list(graph.nodes())
    all_vs_all_matrix = np.zeros((len(nodes), len(nodes)))
    for cluster in clusters:
        for i in cluster:
            for j in cluster:
                all_vs_all_matrix[i, j] = 1
    all_vs_all_df = pd.DataFrame(all_vs_all_matrix, index=nodes, columns=nodes)

    # Compute positions
    pos = nx.spring_layout(graph)

    return graph, nodes, all_vs_all_df, pos


def create_dash_component(graph, nodes, all_vs_all_df, pos):
    """
    Creates the Dash layout and registers callbacks for the heatmap and graph visualization.
    """
    unique_id = str(int(time.time() * 1000))  # Generate a unique ID based on timestamp
    domain_selector_id = f"domain-selector-{unique_id}"
    heatmap_id = f"heatmap-{unique_id}"
    graph_id = f"graph-{unique_id}"

    layout = dbc.Container([
        dbc.Row([
            dbc.Col(dcc.Dropdown(
                id=domain_selector_id,
                options=[{"label": node, "value": node} for node in nodes],
                placeholder="Select one or more domains...",
                multi=True
            ), width=6)
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(dcc.Loading(
                id=f"loading-{unique_id}",
                type="circle",
                children=[
                    dcc.Graph(id=heatmap_id, style={"height": "600px", "width": "100%"}),
                    dcc.Graph(id=graph_id, style={"height": "600px", "width": "100%"})
                ]
            ))
        ])
    ])

    def register_callbacks(app):
        @app.callback(
            [Output(heatmap_id, "figure"), Output(graph_id, "figure")],
            [Input(domain_selector_id, "value")]
        )
        def update_graphs(selected_domains):
            print(f"Callback triggered for {unique_id}")
            if not selected_domains:
                filtered_nodes = nodes
                filtered_edges = list(graph.edges())
                filtered_matrix = all_vs_all_df
            else:
                filtered_edges = [
                    (u, v) for u, v in graph.edges()
                    if u in selected_domains or v in selected_domains
                ]
                filtered_nodes = list(set(node for edge in filtered_edges for node in edge))
                filtered_matrix = all_vs_all_df.loc[filtered_nodes, filtered_nodes]

            if filtered_matrix.empty or not filtered_nodes:
                heatmap_fig = px.imshow([], title="No Data Available")
                graph_fig = go.Figure()
                graph_fig.update_layout(title="No Data Available")
                return heatmap_fig, graph_fig

            # Heatmap
            heatmap_fig = px.imshow(
                filtered_matrix,
                x=filtered_nodes,
                y=filtered_nodes,
                color_continuous_scale="Viridis",
                labels={"x": "Nodes", "y": "Nodes", "color": "Similarity"},
                title="All-vs-All Clustering Matrix"
            )

            # Graph
            edge_x, edge_y = [], []
            for edge in filtered_edges:
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=1.5, color="red"),
                hoverinfo="none",
                mode="lines"
            )

            node_colors = [
                "rgba(255, 100, 100, 0.8)" if node in selected_domains else "rgba(100, 100, 255, 0.5)"
                for node in filtered_nodes
            ]

            node_trace = go.Scatter(
                x=[pos[node][0] for node in filtered_nodes],
                y=[pos[node][1] for node in filtered_nodes],
                mode="markers+text",
                marker=dict(
                    size=12,
                    color=node_colors,
                    showscale=False
                ),
                text=list(filtered_nodes),
                textposition="top center",
                hoverinfo="text"
            )

            graph_fig = go.Figure(data=[edge_trace, node_trace])
            graph_fig.update_layout(
                title="Graph Visualization with Selected Nodes and Neighbors",
                height=600,
                showlegend=False,
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, zeroline=False)
            )

            return heatmap_fig, graph_fig

    return layout, register_callbacks

def create_dash_app(graph, nodes, all_vs_all_df, pos):
    """
    Creates and runs the Dash app.
    """
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1("Markov Clustering Visualization", style={"textAlign": "center", "marginBottom": "30px"}),
        html.Div([
            dcc.Dropdown(
                id="domain-selector",
                options=[{"label": node, "value": node} for node in nodes],
                placeholder="Select one or more domains...",
                multi=True,
                style={"width": "50%", "margin": "auto"}
            ),
            html.Div(
                id="time-estimate",
                style={"textAlign": "center", "marginTop": "10px", "color": "blue"}
            ),
        ], style={"marginBottom": "20px", "textAlign": "center"}),
        dcc.Loading(
            id="loading",
            type="circle",
            children=[
                html.Div(
                    dcc.Graph(id="heatmap", style={"width": "100%", "display": "block"}),
                    style={"marginBottom": "50px"}
                ),
                html.Div(
                    dcc.Graph(id="graph", style={"width": "100%", "display": "block"})
                )
            ],
            style={"marginBottom": "20px"}
        ),
    ])

    @app.callback(
        [Output("heatmap", "figure"), Output("graph", "figure"), Output("time-estimate", "children")],
        [Input("domain-selector", "value")]
    )
    def update_graphs(selected_domains):
        # Handle the case where no domains are selected
        if not selected_domains:
            selected_domains = []

        start_time = time.time()

        # Filter data for selected domains
        if selected_domains:
            filtered_edges = [
                (u, v) for u, v in graph.edges()
                if u in selected_domains or v in selected_domains
            ]
            filtered_nodes = list(set(node for edge in filtered_edges for node in edge))  # Convert set to list
            filtered_matrix = all_vs_all_df.loc[filtered_nodes, filtered_nodes]
        else:
            # Show all domains when no filter is selected
            filtered_nodes = nodes
            filtered_edges = list(graph.edges())
            filtered_matrix = all_vs_all_df

        # Create heatmap
        heatmap_fig = px.imshow(
            filtered_matrix,
            x=filtered_nodes,
            y=filtered_nodes,
            color_continuous_scale="Viridis",
            labels={"x": "Nodes", "y": "Nodes", "color": "Similarity"},
            title="All-vs-All Clustering Matrix"
        )
        heatmap_fig.update_layout(
            autosize=True,
            height=1200,
            margin=dict(l=50, r=50, t=100, b=50),
            xaxis=dict(tickangle=45, automargin=True),
            yaxis=dict(automargin=True),
            coloraxis_colorbar=dict(title="Cluster Similarity", len=0.75)
        )

        # Create graph visualization
        edge_x, edge_y = [], []
        for edge in filtered_edges:
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1.5, color="red"),
            hoverinfo="none",
            mode="lines"
        )

        node_colors = [
            "rgba(255, 100, 100, 0.8)" if node in selected_domains else "rgba(100, 100, 255, 0.5)"
            for node in filtered_nodes
        ]

        node_trace = go.Scatter(
            x=[pos[node][0] for node in filtered_nodes],
            y=[pos[node][1] for node in filtered_nodes],
            mode="markers+text",
            marker=dict(
                size=12,
                color=node_colors,
                showscale=False
            ),
            text=list(filtered_nodes),
            textposition="top center",
            hoverinfo="text"
        )

        graph_fig = go.Figure(data=[edge_trace, node_trace])
        graph_fig.update_layout(
            title="Graph Visualization with Selected Nodes and Neighbors",
            height=1200,
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False),
            margin=dict(l=50, r=50, t=100, b=50)
        )

        end_time = time.time()
        elapsed_time = end_time - start_time
        time_estimate = f"Approximate processing time: {elapsed_time:.2f} seconds"

        return heatmap_fig, graph_fig, time_estimate


    return app

def load_from_cache(file_path):
    try:
        data = joblib.load(file_path)
        print(f"Data loaded from cache: {file_path}")
        return None
    except FileNotFoundError:
        print(f"No cache found at {file_path}")
        return None


def save_to_cache(file_path, data):
    joblib.dump(data, file_path)
    print(f"Data cached at {file_path}")

def utilize_mcl_onNxN(true_positives, cache_dir="cache/"):
    print('Utilize MCL started')
    os.makedirs(cache_dir, exist_ok=True)

    # Cache file paths
    graph_cache = os.path.join(cache_dir, "graph.pkl")
    clusters_cache = os.path.join(cache_dir, "clusters.pkl")
    positions_cache = os.path.join(cache_dir, "positions.pkl")
    matrix_cache = os.path.join(cache_dir, "all_vs_all_matrix.pkl")

    # Load cached data if available
    graph = load_from_cache(graph_cache)
    clusters = load_from_cache(clusters_cache)
    pos = load_from_cache(positions_cache)
    all_vs_all_df = load_from_cache(matrix_cache)

    # Check if any required data is missing
    if graph is None or clusters is None or pos is None or all_vs_all_df is None:
        # Recompute data if cache is missing
        graph = nx.Graph()
        graph.add_edges_from(true_positives)
        save_to_cache(graph_cache, graph)

        # Markov Clustering
        adj_matrix = nx.to_scipy_sparse_array(graph, weight=None)
        adj_matrix = csr_matrix(adj_matrix)
        result = mc.run_mcl(adj_matrix, inflation=1.5)
        clusters = mc.get_clusters(result)
        print("Clusters:", clusters)
        save_to_cache(clusters_cache, clusters)

        # All-vs-All Matrix
        nodes = list(graph.nodes())
        all_vs_all_matrix = np.zeros((len(nodes), len(nodes)))
        for cluster in clusters:
            for i in cluster:
                for j in cluster:
                    all_vs_all_matrix[i, j] = 1
        all_vs_all_df = pd.DataFrame(all_vs_all_matrix, index=nodes, columns=nodes)
        save_to_cache(matrix_cache, all_vs_all_df)

        # Node Positions
        pos = nx.spring_layout(graph)
        save_to_cache(positions_cache, pos)

    # Debug data before returning
    # print("Graph Nodes:", len(graph.nodes()), "Edges:", len(graph.edges()))
    # print("Position Data:", pos)
    # print("Matrix Shape:", all_vs_all_df.shape)
    missing_positions = set(graph.nodes()) - set(pos.keys())
    if missing_positions:
        print("Missing positions for nodes:", missing_positions)

    # Ensure all required data is available before proceeding
    if graph is None or clusters is None or pos is None or all_vs_all_df is None:
        raise ValueError("Required data for visualization is missing or could not be computed.")

    return graph, graph.nodes(), all_vs_all_df, pos

