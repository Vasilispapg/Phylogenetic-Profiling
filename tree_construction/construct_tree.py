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
    Create a distance matrix for the given species list using hierarchical clustering.
    
    Parameters:
    - species: List of species names (SpeciesCode).
    
    Returns:
    - representative_species: List of representative species after clustering.
    - lower_triangle_matrix: Lower triangular distance matrix.
    """
    # Convert species to a numpy array
    species_array = np.array(species)
    # pdb.set_trace()
    # Perform hierarchical clustering using unique species
    cluster_model = AgglomerativeClustering(n_clusters=min(1500, len(species_array) // 3))
    
    # Cluster the species (encoded as unique IDs)
    labels = cluster_model.fit_predict(np.arange(len(species_array)).reshape(-1, 1))
    
    # Map labels back to species
    representative_species = [species_array[i] for i in np.unique(labels)]
    
    # Calculate pairwise distances (numerical indices)
    distances = pdist(np.arange(len(representative_species)).reshape(-1, 1))
    distance_matrix = squareform(distances)

    # Generate the lower triangular matrix
    lower_triangle_matrix = [
        [distance_matrix[i][j] for j in range(i + 1)]
        for i in range(len(representative_species))
    ]
    return representative_species, lower_triangle_matrix

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
    pdb.set_trace()
    dm = DistanceMatrix(names=species, matrix=distance_matrix)
    constructor = DistanceTreeConstructor()
    species_tree = constructor.nj(dm)
    Phylo.write(species_tree, output_path, "newick")
    print(f"Tree saved as {output_path}")