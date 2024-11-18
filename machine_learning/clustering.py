from sklearn.cluster import AgglomerativeClustering, DBSCAN,KMeans
from sklearn.mixture import GaussianMixture
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def clustering_get_groups(correlation_matrix, n_clusters=5):
    print("Performing clustering...")
    model = AgglomerativeClustering(n_clusters=n_clusters, linkage="ward")
    cluster_labels = model.fit_predict(correlation_matrix)

    # Create groups based on clustering results
    groups = {}
    for i, label in enumerate(cluster_labels):
        if label not in groups:
            groups[label] = []
        groups[label].append(correlation_matrix.index[i])  # Use species ID or name as index

    # Visualize clusters in a heatmap
    # sorted_indices = np.argsort(cluster_labels)
    # sorted_matrix = correlation_matrix.iloc[sorted_indices, sorted_indices]
    # sorted_labels = np.array(cluster_labels)[sorted_indices]

    # plt.figure(figsize=(10, 8))
    # sns.heatmap(sorted_matrix, cmap="RdYlGn", annot=False, yticklabels=sorted_labels, xticklabels=False)
    # plt.title("KMeans Clustering of Species Based on Correlation Matrix")
    # plt.ylabel("Cluster Labels")
    # plt.show()

    return groups

def clustering(correlation_matrix, methods=["agglomerative", "dbscan", "gmm", "kmeans"], n_clusters=5):
    print("Performing clustering with multiple methods...")

    # Define subplot grid based on the number of methods
    num_methods = len(methods)
    fig, axes = plt.subplots(1, num_methods, figsize=(5 * num_methods, 8))
    if num_methods == 1:
        axes = [axes]  # Ensure axes is iterable if there's only one subplot

    for ax, method in zip(axes, methods):
        if method == "agglomerative":
            model = AgglomerativeClustering(n_clusters=n_clusters, linkage="ward")
            cluster_labels = model.fit_predict(correlation_matrix)
        elif method == "dbscan":
            model = DBSCAN(eps=3, min_samples=5, metric="euclidean")
            cluster_labels = model.fit_predict(correlation_matrix)
        elif method == "gmm":
            model = GaussianMixture(n_components=n_clusters, random_state=42)
            cluster_labels = model.fit_predict(correlation_matrix)
        elif method == "kmeans":
            model = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = model.fit_predict(correlation_matrix)
        else:
            raise ValueError(f"Clustering method '{method}' not recognized.")

        # Sort the correlation matrix by the cluster labels
        sorted_indices = np.argsort(cluster_labels)
        sorted_matrix = correlation_matrix.iloc[sorted_indices, sorted_indices]
        sorted_labels = np.array(cluster_labels)[sorted_indices]

        # Plot each clustering result in its subplot
        sns.heatmap(
            sorted_matrix,
            cmap="RdYlGn",
            annot=False,
            yticklabels=sorted_labels,
            xticklabels=False,
            ax=ax
        )
        ax.set_title(f"{method.capitalize()} Clustering")
        ax.set_ylabel("Cluster Labels" if ax == axes[0] else "")
        ax.set_xlabel("Species")

    # Adjust layout to prevent overlap
    plt.tight_layout()
    plt.suptitle("Clustering Comparison of Species Correlation Matrix", y=1.02, fontsize=16)
    plt.show()
