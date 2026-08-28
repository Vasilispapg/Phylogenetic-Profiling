# display_tree.py
import logging

from Bio import Phylo
import plotly.graph_objects as go
import numpy as np

from config import TREE_DISPLAY_DEPTH

log = logging.getLogger(__name__)

def convert_tree_to_circular_plotly(tree, max_depth=TREE_DISPLAY_DEPTH):
    """
    Convert a Bio.Phylo tree to circular Plotly-compatible data for interactive visualization.
    """
    def get_coordinates(clade, x, y, angle, depth, coords):
        if depth > max_depth:
            return
        angle_step = 360 / (2 ** depth)
        x_new = x + np.cos(np.radians(angle)) * depth
        y_new = y + np.sin(np.radians(angle)) * depth
        coords.append((clade, x_new, y_new))
        
        if clade.clades:
            for i, subclade in enumerate(clade.clades):
                new_angle = angle + (i - (len(clade.clades) - 1) / 2) * angle_step
                get_coordinates(subclade, x_new, y_new, new_angle, depth + 1, coords)

    coords = []
    get_coordinates(tree.root, 0, 0, 0, 1, coords)
    return coords

def display_tree(tree_filename="species_tree_approx.nw", max_depth=TREE_DISPLAY_DEPTH):
    # Load the tree
    tree = Phylo.read(tree_filename, "newick")
    
    # Convert the tree to circular Plotly-compatible coordinates, limiting depth
    coords = convert_tree_to_circular_plotly(tree, max_depth=max_depth)
    
    # Extract x, y, and text labels for each clade, only showing labels on hover
    x_vals, y_vals, labels = zip(*[(x, y, clade.name or "Unnamed") for clade, x, y in coords if clade.name])

    # Plot the lines (connections between clades)
    lines = []
    for clade, x, y in coords:
        if clade.clades:
            for subclade in clade.clades:
                try:
                    x1, y1 = next((subcl_x, subcl_y) for subcl, subcl_x, subcl_y in coords if subcl == subclade)
                except StopIteration:
                    log.warning("coordinates not found for clade %s", subclade.name)
                    continue  # Skip if coordinates are missing
                lines.append(((x, x1), (y, y1)))

    # Create Plotly figure
    fig = go.Figure()

    # Add lines between clades
    for (x_pair, y_pair) in lines:
        fig.add_trace(go.Scatter(
            x=x_pair, y=y_pair,
            mode='lines',
            line=dict(color='gray', width=1)
        ))

    # Add scatter plot of nodes with hover labels only
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode='markers',
        text=labels,
        marker=dict(size=6, color='blue'),
        hoverinfo='text'  # Only show labels on hover
    ))

    # Update layout for better readability
    fig.update_layout(
        title=f"Interactive Circular Phylogenetic Tree (Depth Limit: {max_depth})",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        showlegend=False,
        height=1000,
        width=1000
    )

    fig.show()
