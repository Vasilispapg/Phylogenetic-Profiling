
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt
import seaborn as sns

def anomaly_detection(correlation_matrix):
    print("Performing anomaly detection...")
    model = IsolationForest(contamination=0.05, random_state=42)
    outliers = model.fit_predict(correlation_matrix)
    print("Outliers detected:", sum(outliers == -1))
    # Visualize outliers on a heatmap (optional)
    outlier_mask = (outliers == -1)
    sns.heatmap(correlation_matrix[outlier_mask], cmap="coolwarm", annot=False)
    plt.title("Anomalies in Species Correlation Matrix")
    plt.show()
    return outliers
