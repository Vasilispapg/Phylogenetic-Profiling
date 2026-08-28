import json
import logging

import numpy as np
import pandas as pd

from config import EVALUE_THRESHOLD
from .utils import extract_species

log = logging.getLogger(__name__)

BLAST_COLUMNS = [
    'QueryID', 'SubjectID', 'PercentIdentity', 'AlignmentLength', 'Mismatches',
    'GapOpens', 'QueryStart', 'QueryEnd', 'SubjectStart', 'SubjectEnd',
    'EValue', 'BitScore',
]


def _load_blast(blast_file_path, evalue_threshold=EVALUE_THRESHOLD):
    """
    Load a tab-separated BLAST tabular file with named columns.

    The E-value cutoff lives HERE, not in the individual matrix builders, so the
    correlation matrix and the feature matrix agree on what "present" means. They
    used to disagree: only the correlation matrix filtered, which silently gave
    the two files different presence semantics even though the same tools accept
    both. Pass ``evalue_threshold=None`` to keep every reported hit.
    """
    blast_df = pd.read_csv(
        blast_file_path, sep='\t', header=None, names=BLAST_COLUMNS
    )
    if evalue_threshold is not None:
        evalues = pd.to_numeric(blast_df['EValue'], errors='coerce')
        kept = evalues <= evalue_threshold
        dropped = int((~kept).sum())
        if dropped:
            log.info("e-value filter (<= %g) dropped %d of %d hits",
                     evalue_threshold, dropped, len(blast_df))
        blast_df = blast_df[kept]
    # Coerce the numeric columns once. Without this a malformed field leaves the
    # whole column as object dtype, and .sum()/.min() silently do string maths.
    for column in ('PercentIdentity', 'AlignmentLength', 'BitScore', 'EValue'):
        blast_df[column] = pd.to_numeric(blast_df[column], errors='coerce')

    blast_df['Domain'] = blast_df['QueryID']
    blast_df['Species'] = blast_df['SubjectID'].apply(extract_species)
    return blast_df


def create_correlation_matrix(blast_file_path, output_path="output/correlation_matrix.csv",
                              using_pi=False, evalue_threshold=EVALUE_THRESHOLD):
    """
    Parse the BLAST file and create a matrix where rows are species and columns
    are domains. Cells are hit counts (or mean percent identity when using_pi).

    A homology is only counted as "present" when its E-value is at or below
    ``evalue_threshold`` (default 1e-5). This keeps presence/absence profiles
    meaningful for downstream profiling/clustering. Pass ``evalue_threshold=None``
    to count every reported hit.
    """
    blast_df = _load_blast(blast_file_path, evalue_threshold)

    heatmap_data = pd.pivot_table(
        blast_df,
        index='Species',
        columns='Domain',
        values='PercentIdentity' if using_pi else None,
        aggfunc='mean' if using_pi else 'size',
        fill_value=0,
    )

    if using_pi and output_path.endswith(".csv"):
        output_path = output_path[:-len(".csv")] + "_pi.csv"

    heatmap_data.to_csv(output_path)
    log.info("correlation matrix (%d species x %d domains) saved to %s",
             *heatmap_data.shape, output_path)
    return heatmap_data


def create_feature_matrix(blast_file_path, output_path="output/feature_matrix.csv",
                          evalue_threshold=EVALUE_THRESHOLD):
    """
    Create a feature matrix where rows are species and columns are domains.
    Each cell is a JSON feature vector aggregating the BLAST hits for that
    (species, domain) pair. Uses the same species key AND the same E-value cutoff
    as the correlation matrix, so the two files are directly comparable.
    """
    blast_df = _load_blast(blast_file_path, evalue_threshold)
    if blast_df.empty:
        raise ValueError(
            "No BLAST hits passed the E-value filter; cannot build a feature matrix."
        )

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

    grouped['FeatureVector'] = _feature_vectors(grouped)

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
    log.info("feature matrix (%d species x %d domains) saved to %s",
             feature_matrix.shape[0], feature_matrix.shape[1] - 1, output_path)
    return feature_matrix


# Key order is part of the on-disk format; keep it stable.
_FEATURE_TEMPLATE = (
    '{"mean_percent_identity": %r, "mean_alignment_length": %r, '
    '"mean_bitscore": %r, "num_hits": %d, "min_evalue": %r}'
)


def _feature_vectors(grouped):
    """
    Serialise one JSON feature vector per (species, domain) row.

    ``DataFrame.apply(..., axis=1)`` builds a Series per row: measured at 0.48 s
    of the 1.02 s spent building the feature matrix for the bundled dataset.
    Formatting from zipped numpy arrays instead is 6.6x faster and produces
    byte-identical output (asserted in tests/test_pipeline.py).

    ``%r`` on a float matches ``json.dumps`` except for non-finite values, where
    json writes ``NaN``/``Infinity``; those rows fall back to the slow path.
    """
    columns = ['mean_percent_identity', 'mean_alignment_length',
               'mean_bitscore', 'num_hits', 'min_evalue']
    arrays = [grouped[c].to_numpy() for c in columns]

    if not all(np.isfinite(a).all() for a in arrays):
        log.warning("non-finite feature values present; using the slow JSON path")
        return grouped.apply(lambda row: json.dumps({
            "mean_percent_identity": row['mean_percent_identity'],
            "mean_alignment_length": row['mean_alignment_length'],
            "mean_bitscore": row['mean_bitscore'],
            "num_hits": int(row['num_hits']),
            "min_evalue": row['min_evalue'],
        }), axis=1)

    lists = [a.tolist() for a in arrays]
    return pd.Series([_FEATURE_TEMPLATE % values for values in zip(*lists)],
                     index=grouped.index)


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
