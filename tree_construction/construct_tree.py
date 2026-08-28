import logging

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform

from tree_construction.nj import build_newick, check_size

log = logging.getLogger(__name__)


def load_profile_matrix(profile_matrix_path):
    """
    Load a species x domain matrix (the correlation matrix produced by
    ``create_correlation_matrix``) and return a cleaned presence/absence
    profile.

    Returns:
        species: list[str] of species identifiers (unique, order preserved).
        profiles: 2D numpy bool array, one row per species.

    Edge cases handled:
        - duplicate species labels are aggregated (logical OR of profiles);
        - species whose entire profile is zero (no domain hits) are dropped,
          since their pairwise Jaccard distance is undefined (0/0);
    """
    matrix = pd.read_csv(profile_matrix_path, index_col=0)

    if matrix.shape[1] == 0:
        raise ValueError("Profile matrix has no domain columns.")

    # Presence/absence; any non-zero / non-NaN count means the domain is present.
    presence = matrix.fillna(0).to_numpy() > 0
    presence_df = pd.DataFrame(presence, index=matrix.index.astype(str))

    # Aggregate duplicate species labels (OR of their profiles).
    if not presence_df.index.is_unique:
        presence_df = presence_df.groupby(level=0).max()

    # Drop species with an all-zero profile (Jaccard undefined for 0/0 pairs).
    non_empty = presence_df.to_numpy().any(axis=1)
    dropped = int((~non_empty).sum())
    if dropped:
        log.warning("dropping %d species with empty profiles", dropped)
    presence_df = presence_df[non_empty]

    species = presence_df.index.tolist()
    profiles = presence_df.to_numpy(dtype=bool)
    return species, profiles


def compute_square_distances(profile_matrix_path, metric="jaccard"):
    """
    Build a **square numpy** distance matrix from a species x domain profile.

    This is the form every tree builder actually wants. Prefer it over
    :func:`compute_distance_matrix`, which materialises the same data as a Python
    list-of-lists (n^2/2 float objects -- gigabytes once n reaches a few thousand).
    """
    species, profiles = load_profile_matrix(profile_matrix_path)

    if len(species) < 2:
        raise ValueError(
            f"Need at least 2 species to build a tree, got {len(species)}."
        )

    condensed = pdist(profiles, metric=metric)
    # Guard against any NaN that a metric might still produce (e.g. constant rows).
    condensed = np.nan_to_num(condensed, nan=1.0)
    distance_matrix = squareform(condensed)
    np.fill_diagonal(distance_matrix, 0.0)
    return species, distance_matrix


def compute_distance_matrix(profile_matrix_path, metric="jaccard"):
    """
    Lower-triangular form of :func:`compute_square_distances`.

    Kept for the CLI and for callers that need Bio.Phylo's ``DistanceMatrix``
    layout (row ``i`` has ``i + 1`` entries, diagonal == 0). Materialising this
    costs O(n^2) Python floats, so new code should use
    :func:`compute_square_distances` instead.
    """
    species, distance_matrix = compute_square_distances(profile_matrix_path, metric)
    lower_triangle_matrix = [
        [float(distance_matrix[i][j]) for j in range(i + 1)]
        for i in range(len(species))
    ]
    return species, lower_triangle_matrix


def _as_square(distance_matrix, n):
    """Accept either a square array or a Bio.Phylo-style lower triangle."""
    if isinstance(distance_matrix, np.ndarray) and distance_matrix.ndim == 2 \
            and distance_matrix.shape == (n, n):
        return np.asarray(distance_matrix, dtype=np.float64)
    square = np.zeros((n, n), dtype=np.float64)
    for i, row in enumerate(distance_matrix):
        for j, value in enumerate(row):
            square[i, j] = square[j, i] = float(value)
    np.fill_diagonal(square, 0.0)
    return square


def construct_tree(species, distance_matrix, output_path="output/species_tree_approx.nw",
                   method="nj"):
    """
    Build a phylogenetic tree from a distance matrix and save it as Newick.

    ``distance_matrix`` may be a square numpy array or a lower-triangular list of
    lists. ``method`` is ``"nj"`` (Neighbour-Joining, the default) or ``"upgma"``.
    """
    species = [str(s) for s in species]
    check_size(len(species), method)
    if len(species) != len(set(species)):
        raise ValueError("Species names must be unique to build a tree.")

    square = _as_square(distance_matrix, len(species))
    log.info("constructing %s tree for %d species", method.upper(), len(species))
    newick = build_newick(square, species, method)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(newick + "\n")
    log.info("tree saved to %s", output_path)
    return output_path
