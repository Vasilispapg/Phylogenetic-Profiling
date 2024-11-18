import pandas as pd

def feature_engineering(correlation_matrix):
    print("Performing feature engineering...")
    # Extract summary statistics for each species
    features = pd.DataFrame({
        "mean_correlation": correlation_matrix.mean(axis=1),
        "std_correlation": correlation_matrix.std(axis=1),
        "max_correlation": correlation_matrix.max(axis=1),
        "min_correlation": correlation_matrix.min(axis=1)
    })
    print(features.head())
    return features