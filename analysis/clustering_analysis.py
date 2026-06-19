import os
import time
from collections import defaultdict

import markov_clustering as mc
import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from networkx.algorithms.community import modularity
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import plotly.express as px
import dash_bootstrap_components as dbc

# Defaults for domain-profile clustering.
DEFAULT_THRESHOLD = 0.5   # minimum Jaccard similarity to draw a domain-domain edge
DEFAULT_INFLATION = 2.0   # MCL granularity


def _dash_debug():
    """Dash debug mode is off unless explicitly enabled via env var."""
    return os.environ.get("DASH_DEBUG", "").lower() in ("1", "true", "yes")

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

# --------------------------------------------------------------------------- #
# Domain-profile clustering (phylogenetic profiling)
#
# Phylogenetic profiling groups domains that share the same presence/absence
# pattern across species. We therefore cluster a DOMAIN x DOMAIN similarity
# graph (not the raw bipartite species-domain graph): an edge connects two
# domains whose binary profiles are similar (Jaccard >= threshold), and MCL
# finds the modules. validate_clusters() reports whether the result is
# meaningful.
# --------------------------------------------------------------------------- #
def domain_jaccard(corr_df):
    """Return (domains, JxJ Jaccard-similarity matrix) from a species x domain
    correlation matrix (presence == value > 0)."""
    B = (corr_df.to_numpy() > 0).astype(float)        # species x domains
    domains = [str(c) for c in corr_df.columns]
    inter = B.T @ B                                    # shared species per domain pair
    pres = B.sum(axis=0)
    union = pres[:, None] + pres[None, :] - inter
    with np.errstate(divide="ignore", invalid="ignore"):
        J = np.where(union > 0, inter / union, 0.0)
    np.fill_diagonal(J, 0.0)
    return domains, J


def build_domain_graph(domains, J, threshold):
    """Weighted domain graph: edge (a, b) with weight J[a,b] when J >= threshold."""
    graph = nx.Graph()
    graph.add_nodes_from(domains)
    iu, ju = np.triu_indices(len(domains), k=1)
    mask = J[iu, ju] >= threshold
    for a, b in zip(iu[mask], ju[mask]):
        graph.add_edge(domains[a], domains[b], weight=float(J[a, b]))
    return graph


def validate_clusters(graph, clusters, nodes):
    """
    Quality report for an MCL partition. MCL is unsupervised (there is no
    training), so we report:
      - cluster count / sizes,
      - modularity Q of the partition on the similarity graph,
      - same-protein co-clustering rate: an internal ground truth -- domains of
        the same protein accession (prefix before the first '-') are physically
        linked and should land in the same cluster,
      - a warning when the partition collapses to one big group (no structure).
    """
    sizes = sorted((len(c) for c in clusters), reverse=True)
    label = {}
    for ci, c in enumerate(clusters):
        for i in c:
            label[nodes[i]] = ci

    partition = [set(nodes[i] for i in c) for c in clusters]
    try:
        q = float(modularity(graph, partition, weight="weight"))
    except Exception:
        q = float("nan")

    groups = defaultdict(list)
    for node in nodes:
        groups[str(node).split("-")[0]].append(node)
    same_pairs = [
        (a, b)
        for members in groups.values() if len(members) > 1
        for x, a in enumerate(members) for b in members[x + 1:]
    ]
    if same_pairs:
        same_rate = float(np.mean([
            1.0 if label.get(a) == label.get(b) else 0.0 for a, b in same_pairs
        ]))
    else:
        same_rate = float("nan")

    largest = sizes[0] if sizes else 0
    warning = None
    if nodes and (largest >= 0.8 * len(nodes) or (q == q and q < 0.05)):
        warning = (
            "Little/no community structure (modularity ~0; one dominant cluster). "
            "The domain profiles are too uniform to form meaningful modules. "
            "Consider a stricter presence threshold (e-value/bitscore cutoff) when "
            "building the correlation matrix, a higher Jaccard threshold, or richer data."
        )

    return {
        "n_domains": len(nodes),
        "n_clusters": len(clusters),
        "n_nontrivial_clusters": sum(1 for s in sizes if s > 1),
        "largest_cluster": largest,
        "cluster_sizes_top": sizes[:10],
        "modularity": round(q, 4) if q == q else None,
        "same_protein_cocluster_rate": round(same_rate, 4) if same_rate == same_rate else None,
        "warning": warning,
    }


def cluster_domains(corr_matrix_path, cache_dir="cache/", threshold=DEFAULT_THRESHOLD,
                    inflation=DEFAULT_INFLATION, run_dash=False):
    """
    Cluster domains by shared phylogenetic profile and return data for the UI:
    (graph, nodes, all_vs_all_df, pos). Also prints a validation report.
    """
    corr_df = pd.read_csv(corr_matrix_path, index_col=0)
    domains, J = domain_jaccard(corr_df)

    graph = build_domain_graph(domains, J, threshold)

    mcl_start = time.time()
    adj = csr_matrix(nx.to_scipy_sparse_array(graph, nodelist=domains, weight="weight"))
    clusters = mc.get_clusters(mc.run_mcl(adj, inflation=inflation))
    print(f"MCL on {len(domains)} domains: {len(clusters)} clusters "
          f"in {time.time() - mcl_start:.2f}s")

    # Domain x domain co-cluster (all-vs-all) matrix.
    co = np.zeros((len(domains), len(domains)))
    for cluster in clusters:
        for i in cluster:
            for j in cluster:
                co[i, j] = 1
    all_vs_all_df = pd.DataFrame(co, index=domains, columns=domains)

    pos = nx.spring_layout(graph)

    metrics = validate_clusters(graph, clusters, domains)
    print("Cluster validation:", metrics)
    if metrics["warning"]:
        print("WARNING:", metrics["warning"])

    if run_dash:
        app = create_dash_app(graph, list(graph.nodes()), all_vs_all_df, pos)
        app.run(debug=_dash_debug(), port=8051)
        return

    return graph, list(graph.nodes()), all_vs_all_df, pos

