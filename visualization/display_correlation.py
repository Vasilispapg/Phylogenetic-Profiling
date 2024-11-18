# display_correlation.py
import plotly.graph_objects as go
import pandas as pd

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
