import json

import numpy as np
import pandas as pd

from .utils import extract_species

BLAST_COLUMNS = [
    'QueryID', 'SubjectID', 'PercentIdentity', 'AlignmentLength', 'Mismatches',
    'GapOpens', 'QueryStart', 'QueryEnd', 'SubjectStart', 'SubjectEnd',
    'EValue', 'BitScore',
]


def _load_blast(blast_file_path):
    """Load a tab-separated BLAST tabular file with named columns."""
    blast_df = pd.read_csv(
        blast_file_path, sep='\t', header=None, names=BLAST_COLUMNS
    )
    blast_df['Domain'] = blast_df['QueryID']
    blast_df['Species'] = blast_df['SubjectID'].apply(extract_species)
    return blast_df


def create_correlation_matrix(blast_file_path, output_path="output/correlation_matrix.csv",
                              using_pi=False, evalue_threshold=1e-5):
    """
    Parse the BLAST file and create a matrix where rows are species and columns
    are domains. Cells are hit counts (or mean percent identity when using_pi).

    A homology is only counted as "present" when its E-value is at or below
    ``evalue_threshold`` (default 1e-5). This keeps presence/absence profiles
    meaningful for downstream profiling/clustering. Pass ``evalue_threshold=None``
    to count every reported hit.
    """
    blast_df = _load_blast(blast_file_path)

    if evalue_threshold is not None:
        evalues = pd.to_numeric(blast_df['EValue'], errors='coerce')
        blast_df = blast_df[evalues <= evalue_threshold]

    heatmap_data = pd.pivot_table(
        blast_df,
        index='Species',
        columns='Domain',
        values='PercentIdentity' if using_pi else None,
        aggfunc='mean' if using_pi else 'size',
        fill_value=0,
    )

    if using_pi:
        output_path = output_path.replace(".csv", "_pi.csv")

    heatmap_data.to_csv(output_path)
    print(f"Correlation matrix saved to {output_path}")
    return heatmap_data


def create_feature_matrix(blast_file_path, output_path="output/feature_matrix.csv"):
    """
    Create a feature matrix where rows are species and columns are domains.
    Each cell is a JSON feature vector aggregating the BLAST hits for that
    (species, domain) pair. Uses the same species key as the correlation matrix.
    """
    blast_df = _load_blast(blast_file_path)

    grouped = blast_df.groupby(['Species', 'Domain']).agg(
        total_percent_identity=('PercentIdentity', 'sum'),
        total_alignment_length=('AlignmentLength', 'sum'),
        total_bitscore=('BitScore', 'sum'),
        num_hits=('PercentIdentity', 'count'),
        min_evalue=('EValue', 'min'),
    ).reset_index()

    grouped = grouped[grouped['num_hits'] > 0]

    grouped['mean_percent_identity'] = grouped['total_percent_identity'] / grouped['num_hits']
    grouped['mean_alignment_length'] = grouped['total_alignment_length'] / grouped['num_hits']
    grouped['mean_bitscore'] = grouped['total_bitscore'] / grouped['num_hits']

    grouped['FeatureVector'] = grouped.apply(lambda row: json.dumps({
        "mean_percent_identity": row['mean_percent_identity'],
        "mean_alignment_length": row['mean_alignment_length'],
        "mean_bitscore": row['mean_bitscore'],
        "num_hits": int(row['num_hits']),
        "min_evalue": row['min_evalue'],
    }), axis=1)

    empty_vector = json.dumps({
        "mean_percent_identity": 0,
        "mean_alignment_length": 0,
        "mean_bitscore": 0,
        "num_hits": 0,
        "min_evalue": 0,
    })
    feature_matrix = grouped.pivot(
        index='Species', columns='Domain', values='FeatureVector'
    ).fillna(empty_vector)

    feature_matrix.reset_index(inplace=True)
    feature_matrix.to_csv(output_path, index=False)
    print(f"Feature matrix saved to {output_path}")
    return feature_matrix


def find_true_positives(corr_matrix_path):
    """
    Return the list of (species, domain) pairs that have a non-zero value in the
    correlation matrix (i.e. the domain is present in that species).
    """
    corr_matrix = pd.read_csv(corr_matrix_path, index_col=0)
    if corr_matrix.empty:
        return []

    species = corr_matrix.index.to_numpy()
    domains = corr_matrix.columns.to_numpy()
    rows, cols = np.where(corr_matrix.to_numpy() > 0)
    return [(species[r], domains[c]) for r, c in zip(rows, cols)]
