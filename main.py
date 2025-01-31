import sys
import pandas as pd
from tree_construction.construct_tree import load_species_data, approximate_distance_matrix, construct_tree
from tree_construction.display_tree import display_tree
from analysis.matrix_operations import create_correlation_matrix, create_feature_matrix, find_true_positives
from analysis.clustering_analysis import utilize_mcl_onNxN
from visualization.display_correlation import (
    display_species_domain_heatmap, display_species_domain_heatmap_with_features
)
from visualization.display_species_correlation import display_heatmap_speciesxspecies

# Constants
SPECIES_LIST_PATH = "data/list.2"
BLAST_FILE_PATH = "data/Sequences-218-annot.Query.blastp"
OUTPUT_DIR = "output"
TREE_FILE_PATH = f"{OUTPUT_DIR}/species_tree_approx.nw"
CORRELATION_MATRIX_PATH = f"{OUTPUT_DIR}/correlation_matrix.csv"
FEATURE_MATRIX_PATH = f"{OUTPUT_DIR}/feature_matrix.csv"
DOMAIN_CORRELATION_MATRIX_PATH = f"{OUTPUT_DIR}/domain_correlation_matrix.csv"
DEFAULT_TREE_DEPTH = 64

def construct_tree_command():
    species_df = load_species_data(SPECIES_LIST_PATH)
    representative_species, lower_triangle_matrix = approximate_distance_matrix(species_df)
    construct_tree(representative_species, lower_triangle_matrix)

def display_tree_command():
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TREE_DEPTH
    display_tree(TREE_FILE_PATH, max_depth=depth)
    
def all_vs_all_command():
    utilize_mcl_onNxN(find_true_positives(CORRELATION_MATRIX_PATH),create_dash_app=True)
    
def analyze_command():
    create_correlation_matrix(BLAST_FILE_PATH)
    create_feature_matrix(BLAST_FILE_PATH)

def display_cor_command():
    display_species_domain_heatmap(CORRELATION_MATRIX_PATH)

def display_cor_features_command():
    display_species_domain_heatmap_with_features(FEATURE_MATRIX_PATH)

def display_heatmap_spxsp_command():
    display_heatmap_speciesxspecies(CORRELATION_MATRIX_PATH)
    display_heatmap_speciesxspecies(DOMAIN_CORRELATION_MATRIX_PATH)

COMMANDS = {
    "--construct_tree": construct_tree_command,
    "--display_tree": display_tree_command,
    "--analyze": analyze_command,
    "--display_cor": display_cor_command,
    "--display_cor_features": display_cor_features_command,
    "--display_heatmap_spxsp": display_heatmap_spxsp_command,
    "--all_vs_all": all_vs_all_command,
}

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py [command]")
        print(f"Available commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    command = sys.argv[1]
    command_function = COMMANDS.get(command)

    if not command_function:
        print(f"Invalid command: {command}")
        print(f"Available commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    try:
        command_function()
    except Exception as e:
        print(f"An error occurred while executing '{command}': {e}")

if __name__ == "__main__":
    main()