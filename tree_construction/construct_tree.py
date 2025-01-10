import pandas as pd
from Bio.Phylo.TreeConstruction import DistanceTreeConstructor, DistanceMatrix
from sklearn.cluster import AgglomerativeClustering
from scipy.spatial.distance import pdist, squareform
from Bio import Phylo
import pdb
import numpy as np
import sys

def load_species_data(species_list_path):
    """
    Load the species data from the given file.
    
    Parameters:
    - species_list_path: Path to the species list file (e.g., list.2).
    
    Returns:
    - species_list: List of species names extracted from the file.
    """
    species_df = pd.read_csv(species_list_path, sep='-', names=['TaxID', 'SpeciesCode'], engine='python')
    # Create unique identifiers by combining TaxID and SpeciesCode
    species_list = (species_df['TaxID'].astype('str') + '-' + species_df['SpeciesCode']).tolist()
    return species_list

def approximate_distance_matrix(species):
    """
    Create a full distance matrix for the given species list.
    
    Parameters:
    - species: List of species names (SpeciesCode).
    
    Returns:
    - species: Original list of species.
    - lower_triangle_matrix: Lower triangular distance matrix.
    """
    # Convert species to numerical indices for distance calculation
    species_indices = np.arange(len(species)).reshape(-1, 1)
    
    # Calculate pairwise distances (use indices to simulate distances)
    distances = pdist(species_indices)
    distance_matrix = squareform(distances)

    # Generate the lower triangular matrix
    lower_triangle_matrix = [
        [distance_matrix[i][j] for j in range(i + 1)]
        for i in range(len(species))
    ]
    return species, lower_triangle_matrix


def construct_tree(species, distance_matrix, output_path="output/species_tree_approx.nw"):
    """
    Construct a phylogenetic tree using the given species and distance matrix.
    
    Parameters:
    - species: List of species names.
    - distance_matrix: Lower triangular distance matrix.
    - output_path: Path to save the constructed tree in Newick format.
    """
    # Increase Python's recursion limit if needed
    sys.setrecursionlimit(10000)
    # Ensure species names are strings
    species = [str(s) for s in species]
    # pdb.set_trace()
    print(f"Constructing tree for {len(species)} species...")
    dm = DistanceMatrix(names=species, matrix=distance_matrix)
    print("Distance matrix created.")
    constructor = DistanceTreeConstructor()
    print("Constructing tree...")
    species_tree = constructor.nj(dm)
    print("Tree constructed.")
    Phylo.write(species_tree, output_path, "newick")
    print(f"Tree saved as {output_path}")