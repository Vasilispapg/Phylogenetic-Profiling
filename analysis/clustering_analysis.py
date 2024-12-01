import markov_clustering as mc
import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
import pandas as pd
from dash import Dash
from dash import dcc, html
import plotly.express as px
import plotly.graph_objects as go


def utilize_mcl_onNxN(true_positives):
    # Step 2: Create a graph
    graph = nx.Graph()
    graph.add_edges_from(true_positives)

    # Convert to sparse adjacency matrix
    adj_matrix = nx.to_scipy_sparse_array(graph, weight=None)

    # Ensure the matrix is in CSR format
    adj_matrix = csr_matrix(adj_matrix)

    # Run MCL
    result = mc.run_mcl(adj_matrix, inflation=1.5)
    clusters = mc.get_clusters(result)
    # print("Clusters:", clusters)

    # Rebuild the all-vs-all matrix based on clustering
    nodes = list(graph.nodes())
    all_vs_all_matrix = np.zeros((len(nodes), len(nodes)))
    for cluster in clusters:
        for i in cluster:
            for j in cluster:
                all_vs_all_matrix[i, j] = 1

    # Create a pandas DataFrame for the all-vs-all matrix
    all_vs_all_df = pd.DataFrame(all_vs_all_matrix, index=nodes, columns=nodes)

    # Graph positions for visualization
    pos = nx.spring_layout(graph)

    # Build Dash App
    app = Dash(__name__)

    # Heatmap for all-vs-all matrix
    heatmap_fig = px.imshow(
        all_vs_all_df,
        x=nodes,
        y=nodes,
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

    # Graph visualization with clusters
    cluster_colors = {node: i for i, cluster in enumerate(clusters) for node in cluster}
    node_colors = [cluster_colors.get(node, -1) for node in graph.nodes()]
    edge_x, edge_y = [], []
    for edge in graph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color="#888"),
        hoverinfo="none",
        mode="lines"
    )
    node_trace = go.Scatter(
        x=[pos[node][0] for node in graph.nodes()],
        y=[pos[node][1] for node in graph.nodes()],
        mode="markers+text",
        marker=dict(
            size=12,
            color=node_colors,
            colorscale="Viridis",
            showscale=True
        ),
        text=list(graph.nodes()),
        textposition="top center",
        hoverinfo="text"
    )
    graph_fig = go.Figure(data=[edge_trace, node_trace])
    graph_fig.update_layout(
        title="Graph Visualization with Clusters",
        height=800,
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False, zeroline=False),
        margin=dict(l=50, r=50, t=100, b=50)
    )

    # Dash layout
    app.layout = html.Div([
        html.H1("Markov Clustering Visualization", style={"textAlign": "center", "marginBottom": "30px"}),
        html.Div(
            dcc.Graph(figure=heatmap_fig, style={"width": "100%", "display": "block"}),
            style={"marginBottom": "50px"}
        ),
        html.Div(
            dcc.Graph(figure=graph_fig, style={"width": "100%", "display": "block"})
        )
    ])

    # Run the Dash app
    app.run_server(debug=True, port=8050)  
    