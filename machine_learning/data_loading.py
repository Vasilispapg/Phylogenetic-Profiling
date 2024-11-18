import pandas as pd
def load_data(correlation_data_path="domain_correlation_matrix.csv"):
    # Load the correlation data and scale it to 0-100
    domain_data = pd.read_csv(correlation_data_path, index_col=0)
    species_correlation = domain_data.T.corr() * 100
    return species_correlation