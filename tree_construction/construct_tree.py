import sys

import numpy as np
import pandas as pd
from Bio import Phylo
from Bio.Phylo.TreeConstruction import DistanceMatrix, DistanceTreeConstructor
from scipy.spatial.distance import pdist, squareform


def load_species_data(species_list_path):
    """
    Load a plain species list file (e.g. ``data/list.2``) of the form
    ``TaxID-SpeciesCode`` per line.

    Returns a list of unique ``TaxID-SpeciesCode`` identifiers.

    NOTE: A bare species list carries no information from which a meaningful
    phylogenetic distance can be derived.  For real tree construction use
    :func:`compute_distance_matrix`, which derives distances from a
    species x domain presence/absence profile (the correlation matrix).
    """
    species_df = pd.read_csv(
        species_list_path, sep='-', names=['TaxID', 'SpeciesCode'], engine='python'
    )
    species_list = (
        species_df['TaxID'].astype('str') + '-' + species_df['SpeciesCode']
    ).tolist()
    return species_list


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
    dropped = (~non_empty).sum()
    if dropped:
        print(f"Warning: dropping {dropped} species with empty profiles.")
    presence_df = presence_df[non_empty]

    species = presence_df.index.tolist()
    profiles = presence_df.to_numpy(dtype=bool)
    return species, profiles


def compute_distance_matrix(profile_matrix_path, metric="jaccard"):
    """
    Build a lower-triangular distance matrix from a species x domain profile.

    Distances are computed between species' domain presence/absence profiles
    (default: Jaccard), which is the standard basis for a phylogenetic-profiling
    tree.

    Returns:
        species: list[str]
        lower_triangle_matrix: list[list[float]] suitable for Bio.Phylo's
            ``DistanceMatrix`` (row ``i`` has ``i + 1`` entries, diagonal == 0).
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

    lower_triangle_matrix = [
        [float(distance_matrix[i][j]) for j in range(i + 1)]
        for i in range(len(species))
    ]
    return species, lower_triangle_matrix


def construct_tree(species, distance_matrix, output_path="output/species_tree_approx.nw"):
    """
    Construct a Neighbour-Joining phylogenetic tree from a lower-triangular
    distance matrix and save it as Newick.
    """
    if len(species) < 2:
        raise ValueError("Cannot construct a tree from fewer than 2 species.")
    if len(species) != len(set(species)):
        raise ValueError("Species names must be unique to build a DistanceMatrix.")

    # NJ on deep/large inputs can recurse deeply when serialising the tree.
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))

    species = [str(s) for s in species]
    print(f"Constructing tree for {len(species)} species...")
    dm = DistanceMatrix(names=species, matrix=distance_matrix)
    print("Distance matrix created.")
    constructor = DistanceTreeConstructor()
    print("Constructing tree (this is O(n^3); large inputs may be slow)...")
    species_tree = constructor.nj(dm)
    print("Tree constructed.")
    Phylo.write(species_tree, output_path, "newick")
    print(f"Tree saved as {output_path}")
    return output_path
