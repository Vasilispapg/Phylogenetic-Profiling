import pandas as pd
import json
from .utils import extract_species,extract_partial_species

def create_correlation_matrix(blast_file_path, output_path="output/correlation_matrix.csv", using_pi=True):
    """
    Parse the BLAST file and create a correlation matrix where rows are species and columns are domains.
    """
    blast_df = pd.read_csv(
        blast_file_path,
        sep='\t',
        header=None,
        names=['QueryID', 'SubjectID', 'PercentIdentity', 'AlignmentLength', 'Mismatches', 'GapOpens',
               'QueryStart', 'QueryEnd', 'SubjectStart', 'SubjectEnd', 'EValue', 'BitScore']
    )
    blast_df['Domain'] = blast_df['QueryID']
    blast_df['Species'] = blast_df['SubjectID'].apply(extract_species)

    aggfunc = 'mean' if using_pi else 'size'
    heatmap_data = pd.pivot_table(
        blast_df,
        index='Species',
        columns='Domain',
        values='PercentIdentity' if using_pi else None,
        aggfunc=aggfunc,
        fill_value=0
    )

    if using_pi:
        output_path = output_path.replace(".csv", "_pi.csv")

    heatmap_data.to_csv(output_path)
    print(f"Correlation matrix saved to {output_path}")
    return heatmap_data

def create_feature_matrix(blast_file_path, output_path="output/feature_matrix.csv"):
    """
    Create a feature matrix where rows are species and columns are domains.
    Each cell contains a JSON-like structure of features.
    """
    blast_df = pd.read_csv(
        blast_file_path,
        sep='\t',
        header=None,
        names=['QueryID', 'SubjectID', 'PercentIdentity', 'AlignmentLength', 'Mismatches', 'GapOpens',
               'QueryStart', 'QueryEnd', 'SubjectStart', 'SubjectEnd', 'EValue', 'BitScore']
    )
    blast_df['Domain'] = blast_df['QueryID']
    blast_df['Species'] = blast_df['SubjectID'].apply(extract_partial_species)

    grouped = blast_df.groupby(['Species', 'Domain'])
    feature_data = grouped.agg(
        mean_percent_identity=('PercentIdentity', 'mean'),
        num_hits=('PercentIdentity', 'count'),
        mean_evalue=('EValue', 'mean'),
        mean_alignment_length=('AlignmentLength', 'mean'),
        mean_bitscore=('BitScore', 'mean'),
        max_bitscore=('BitScore', 'max')
    ).reset_index()

    feature_data['FeatureVector'] = feature_data.apply(
        lambda row: json.dumps({
            "mean_percent_identity": row['mean_percent_identity'],
            "num_hits": row['num_hits'],
            "mean_evalue": row['mean_evalue'],
            "mean_alignment_length": row['mean_alignment_length'],
            "mean_bitscore": row['mean_bitscore'],
            "max_bitscore": row['max_bitscore']
        }), axis=1
    )

    feature_matrix = feature_data.pivot(
        index='Species', columns='Domain', values='FeatureVector'
    ).fillna(json.dumps({
        "mean_percent_identity": 0,
        "num_hits": 0,
        "mean_evalue": 0,
        "mean_alignment_length": 0,
        "mean_bitscore": 0,
        "max_bitscore": 0
    }))
    feature_matrix.reset_index(inplace=True)
    feature_matrix.to_csv(output_path, index=False)
    print(f"Feature matrix with JSON vectors saved to {output_path}")
    return feature_matrix

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

    """
    Aggregate BLAST data by grouping Species (truncated SubjectID) and Domain.
    Calculates median/sum values, counts hits, and keeps unique species grouping.

    Parameters:
    - blast_file_path (str): Path to the BLAST file.
    - output_path (str): Path to save the output aggregated feature matrix.
    """
    # Load the data
    blast_df = pd.read_csv(
        blast_file_path,
        sep='\t',
        header=None,
        names=['QueryID', 'SubjectID', 'PercentIdentity', 'AlignmentLength', 'Mismatches', 'GapOpens',
               'QueryStart', 'QueryEnd', 'SubjectStart', 'SubjectEnd', 'EValue', 'BitScore']
    )

    # Extract Domain and Truncated Species
    blast_df['Domain'] = blast_df['QueryID']
    blast_df['Species'] = blast_df['SubjectID'].apply(extract_partial_species)

    # Group the data by TruncatedSpecies and Domain
    grouped = blast_df.groupby(['Species', 'Domain']).agg(
        median_percent_identity=('PercentIdentity', 'median'),
        total_alignment_length=('AlignmentLength', 'sum'),
        mean_bitscore=('BitScore', 'mean'),
        median_evalue=('EValue', 'median'),
        total_hits=('SubjectID', 'count')
    ).reset_index()

    # Save the aggregated data to a CSV file
    grouped.to_csv(output_path, index=False)
    print(f"Aggregated feature matrix saved to {output_path}")

    return grouped