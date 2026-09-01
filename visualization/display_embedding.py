"""Plot an embedding produced by analysis/embedding.py (the CLI's --show)."""
import plotly.graph_objects as go


def display_embedding(result, names, axis="domains", method="pca"):
    """
    Scatter the projected points, one trace per KMeans cluster.

    A trace per cluster (rather than one trace coloured by label) is what gives
    the legend its click-to-isolate behaviour, which is the only way to read a
    crowded projection.
    """
    coords, labels = result["coords"], result["labels"]
    axis_title = "PC%d" if method == "pca" else "dim %d"

    fig = go.Figure()
    for cluster in sorted(set(labels)):
        points = [(xy, name) for xy, label, name in zip(coords, labels, names)
                  if label == cluster]
        fig.add_trace(go.Scatter(
            x=[xy[0] for xy, _ in points],
            y=[xy[1] for xy, _ in points],
            mode="markers",
            name=f"cluster {cluster} ({len(points)})",
            text=[name for _, name in points],
            hovertemplate="%{text}<extra></extra>",
            marker=dict(size=7, opacity=0.85),
        ))

    title = (f"{len(names)} {axis} projected with {method.upper()}, "
             f"{result['n_clusters']} clusters")
    if result.get("note"):
        title += f"<br><sub>{result['note']}</sub>"
    fig.update_layout(
        title=title,
        xaxis_title=axis_title % 1,
        yaxis_title=axis_title % 2,
        width=900,
        height=700,
        legend=dict(itemsizing="constant"),
    )
    fig.show()
