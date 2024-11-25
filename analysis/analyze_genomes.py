import pandas as pd
from dash import Dash, dcc, html
import plotly.graph_objects as go
import pdb
import markov_clustering as mc
import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
from dash import Dash, dcc, html
import plotly.graph_objects as go
import plotly.express as px

def load_blast_data(protein_domain_path):
    blast_df = pd.read_csv(protein_domain_path, sep='\t', header=None,
                           usecols=[0, 1, 2, 10],
                           names=['QueryID', 'SubjectID', 'PercentIdentity', 'EValue'])
    blast_df['SpeciesCode'] = blast_df['SubjectID'].str.split('-').str[2]
    return blast_df[['QueryID', 'SpeciesCode', 'PercentIdentity', 'EValue']]

def extract_species(subject_id):
    # Split the string by a common delimiter (e.g., '-')
    parts = subject_id.split('-')
    # Recombine parts up to the segment containing the numeric sequence
    for i, part in enumerate(parts):
        if any(char.isdigit() for char in part):  # Stop at the first part containing digits
            return '-'.join(parts[:4])
    return subject_id  # Fallback: return the original string if no digits found

def create_correlation_matrix(blast_file_path, output_path="output/correlation_matrix.csv",using_pi=True):
    """
    Parse the BLAST file and create a matrix where rows are species and columns are domains.

    Parameters:
    - blast_file_path (str): Path to the BLAST file.

    Returns:
    - pd.DataFrame: A DataFrame with species as rows and domains as columns.
    """

    # Read the BLAST file
    blast_df = pd.read_csv(
        blast_file_path,
        sep='\t',
        header=None,
        names=['QueryID', 'SubjectID', 'PercentIdentity', 'AlignmentLength', 'Mismatches', 'GapOpens',
               'QueryStart', 'QueryEnd', 'SubjectStart', 'SubjectEnd', 'EValue', 'BitScore']
    )
    # Extract species and domains
    blast_df['Domain'] = blast_df['QueryID']
    # Apply the extraction logic to the 'SubjectID' column
    blast_df['Species'] = blast_df['SubjectID'].apply(extract_species)
    # Pivot to create a matrix with species as rows and domains as columns
    
    if(using_pi):
        heatmap_data = pd.pivot_table(
            blast_df,
            index='Species',
            columns='Domain',
            values='PercentIdentity',
            aggfunc='mean',  # Calculate the mean percent identity
            fill_value=0      # Fill absence with 0
        )
    else:
        heatmap_data = pd.pivot_table(
            blast_df,
            index='Species',
            columns='Domain',
            aggfunc='size',  # Count occurrences
            fill_value=0      # Fill absence with 0
        )
    # Calculate the correlation matrix
    if(using_pi):
        output_path = output_path.replace(".csv","_pi.csv")
    heatmap_data.to_csv(output_path)
    print(f"Correlation matrix saved to {output_path}")
    return heatmap_data

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
    
def find_true_positives(corr_matrix_path):
    
    # Load the correlation matrix
    corr_matrix = pd.read_csv(corr_matrix_path, index_col=0)
    
    # Find the true positives
    true_positives = []
    # if in the same row exist a value greater than 0, it is a true positive
    # else it is a true negative
    for species in corr_matrix.index:
        for domain in corr_matrix.columns:
            if corr_matrix.loc[species, domain] > 0:
                true_positives.append((species, domain))
    return true_positives

def utilize_mcl_onNxN(true_positives):
    
    # Step 2: Create a graph
    graph = nx.Graph()
    graph.add_edges_from(true_positives)

    # Convert to sparse adjacency matrix
    adj_matrix = nx.to_scipy_sparse_array(graph, weight=None)

    # Ensure the matrix is in CSR format
    adj_matrix = csr_matrix(adj_matrix)

    # Debugging: Print matrix details
    # print("Adjacency Matrix Shape:", adj_matrix.shape)
    # print("Non-zero Elements:", adj_matrix.nnz)

    # Check dense matrix for small examples
    # if adj_matrix.shape[0] <= 10:
        # print("Adjacency Matrix (Dense):", adj_matrix.todense())

    # Try running MCL
    try:
        result = mc.run_mcl(adj_matrix, inflation=1.5)  # Adjust inflation as needed
    except Exception as e:
        print(f"Error during MCL: {e}")
        print("Converting to dense matrix for debugging...")
        # Convert to dense and re-run for debugging
        dense_adj_matrix = adj_matrix.todense()
        result = mc.run_mcl(dense_adj_matrix, inflation=1.5)  # Try with dense matrix

    # Extract clusters
    clusters = mc.get_clusters(result)
    # print("Clusters:", clusters)

    # Step 6: Convert result into an all-vs-all matrix
    # Rebuild the adjacency matrix based on clustering
    nodes = list(graph.nodes())

    # Initialize an all-vs-all matrix with zeros
    all_vs_all_matrix = np.zeros((len(nodes), len(nodes)))

    # Fill in the matrix based on clusters
    for cluster in clusters:
        for i in cluster:
            for j in cluster:
                all_vs_all_matrix[i, j] = 1 
                
    # Convert to a pandas DataFrame for better readability
    all_vs_all_df = pd.DataFrame(
        all_vs_all_matrix,
        index=nodes,
        columns=nodes
    )

    # Save the matrix to a CSV file (optional)
    all_vs_all_df.to_csv("all_vs_all_matrix.csv")
    # print("All-vs-All Matrix:\n", all_vs_all_df)
    
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
    heatmap_fig.update_xaxes(tickangle=45)

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
            size=10,
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
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False, zeroline=False)
    )

    # Dash layout
    app.layout = html.Div([
        html.H1("Markov Clustering Visualization", style={"textAlign": "center"}),
        html.Div([
            dcc.Graph(figure=heatmap_fig, style={"width": "48%", "display": "inline-block"}),
            dcc.Graph(figure=graph_fig, style={"width": "48%", "display": "inline-block"}),
        ])
    ])

    # Run the Dash app
    app.run_server(debug=True, port=8050)
    
    
def create_similarity_matrix(blast_df, output_path="output/domain_similarity_matrix.csv"):
    # Pivot to create a matrix where rows are species, columns are queries, and values are percent identity
    similarity_matrix = blast_df.pivot_table(
        index='SpeciesCode', columns='QueryID', values='PercentIdentity', fill_value=0
    )
    
    # Calculate pairwise correlation between species
    correlation_matrix = similarity_matrix.T.corr()  # Transpose to correlate species
    
    # Save the correlation matrix
    correlation_matrix.to_csv(output_path)
    print(f"Correlation matrix saved as {output_path}")
    
    return correlation_matrix