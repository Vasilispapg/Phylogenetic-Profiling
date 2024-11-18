# display_species_correlation.py
import plotly.graph_objects as go
from scipy.cluster.hierarchy import dendrogram, linkage
import pandas as pd
import numpy as np

def display_heatmap_speciesxspecies(correlation_data_path="correlation_matrix.csv"):
    # Load the domain correlation data
    domain_data = pd.read_csv(correlation_data_path, index_col=0)

    # Calculate pairwise correlation or similarity matrix (NxN matrix)
    species_correlation = domain_data.T.corr() * 100  # Scale correlations to 0-100 for display

    # Perform hierarchical clustering on the species correlation matrix
    species_linkage = linkage(species_correlation, method='average')
    species_dendro = dendrogram(species_linkage, orientation='left', labels=species_correlation.index.tolist(), no_plot=True)

    # Reorder the matrix based on dendrogram leaves
    reordered_matrix = species_correlation.iloc[species_dendro['leaves'], species_dendro['leaves']]

    # Generate hover text for each cell
    hover_text = []
    for i, species1 in enumerate(reordered_matrix.index):
        hover_row = []
        for j, species2 in enumerate(reordered_matrix.columns):
            hover_row.append(f"<b>{species1}</b> vs <b>{species2}</b><br>Correlation: {reordered_matrix.iat[i, j]:.2f}")
        hover_text.append(hover_row)

    # Define the heatmap with an extended color scale (e.g., 0-100)
    heatmap_trace = go.Heatmap(
        z=reordered_matrix.values,
        x=reordered_matrix.columns,
        y=reordered_matrix.index,
        colorscale='YlOrRd',
        colorbar=dict(title='Correlation (%)'),
        zmin=0, zmax=100,  # Set to the scale of your data (0-100)
        text=hover_text,
        hoverinfo="text"
    )

    # Layout adjustments for readability
    fig = go.Figure(data=[heatmap_trace])
    fig.update_layout(
        title="Species Correlation Matrix (%)",
        xaxis=dict(title="Species", tickangle=45, tickmode='array', tickvals=list(range(len(reordered_matrix.columns))), ticktext=reordered_matrix.columns),
        yaxis=dict(title="Species", tickmode='array', tickvals=list(range(len(reordered_matrix.index))), ticktext=reordered_matrix.index),
        width=800,
        height=800,
    )

    fig.show()

