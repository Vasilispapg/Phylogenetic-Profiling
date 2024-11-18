import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

def dimensionality_reduction(correlation_matrix):
    print("Performing dimensionality reduction...")
    pca = PCA(n_components=2)
    reduced_data = pca.fit_transform(correlation_matrix)
    plt.figure(figsize=(8, 6))
    plt.scatter(reduced_data[:, 0], reduced_data[:, 1], cmap='viridis', s=50, alpha=0.7)
    plt.xlabel("PCA Component 1")
    plt.ylabel("PCA Component 2")
    plt.title("PCA Visualization of Species Correlation Matrix")
    plt.colorbar(label="Cluster Labels")
    plt.show()
    return reduced_data
