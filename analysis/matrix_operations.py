import pandas as pd
import json
from .utils import extract_species,extract_partial_species

def create_correlation_matrix(blast_file_path, output_path="output/correlation_matrix.csv", using_pi=False):
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
    Each cell contains aggregated features, excluding zero-hit rows.
    """
    # Load BLAST data
    blast_df = pd.read_csv(
        blast_file_path,
        sep='\t',
        header=None,
        names=['QueryID', 'SubjectID', 'PercentIdentity', 'AlignmentLength', 'Mismatches', 'GapOpens',
               'QueryStart', 'QueryEnd', 'SubjectStart', 'SubjectEnd', 'EValue', 'BitScore']
    )

    # Extract Domain and Species
    blast_df['Domain'] = blast_df['QueryID']
    blast_df['Species'] = blast_df['SubjectID'].str.extract(r'(.*?-\w+-\w+-\w+-[A-Z])')

    # Group by Species and Domain
    grouped = blast_df.groupby(['Species', 'Domain']).agg(
        total_percent_identity=('PercentIdentity', 'sum'),
        total_alignment_length=('AlignmentLength', 'sum'),
        total_bitscore=('BitScore', 'sum'),
        num_hits=('PercentIdentity', 'count'),  # Count hits
        min_evalue=('EValue', 'min')  # Take minimum EValue
    ).reset_index()

    # Exclude rows with zero hits
    grouped = grouped[grouped['num_hits'] > 0]

    # Aggregate and normalize data for each group
    grouped['mean_percent_identity'] = grouped['total_percent_identity'] / grouped['num_hits']
    grouped['mean_alignment_length'] = grouped['total_alignment_length'] / grouped['num_hits']
    grouped['mean_bitscore'] = grouped['total_bitscore'] / grouped['num_hits']

    # Convert to JSON-like feature vector
    grouped['FeatureVector'] = grouped.apply(lambda row: json.dumps({
        "mean_percent_identity": row['mean_percent_identity'],
        "mean_alignment_length": row['mean_alignment_length'],
        "mean_bitscore": row['mean_bitscore'],
        "num_hits": row['num_hits'],
        "min_evalue": row['min_evalue']
    }), axis=1)

    # Pivot to create the feature matrix
    feature_matrix = grouped.pivot(index='Species', columns='Domain', values='FeatureVector').fillna(json.dumps({
        "mean_percent_identity": 0,
        "mean_alignment_length": 0,
        "mean_bitscore": 0,
        "num_hits": 0,
        "min_evalue": 0
    }))

    # Save to CSV
    feature_matrix.reset_index(inplace=True)
    feature_matrix.to_csv(output_path, index=False)
    print(f"Feature matrix saved to {output_path}")
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