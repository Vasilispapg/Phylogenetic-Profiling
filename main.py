import sys
import pandas as pd
from tree_construction.construct_tree import load_species_data, approximate_distance_matrix, construct_tree
from tree_construction.display_tree import display_tree
from analysis.matrix_operations import create_correlation_matrix, create_feature_matrix, find_true_positives
from analysis.heatmap_visualization import run_heatmap_app
from analysis.clustering_analysis import utilize_mcl_onNxN
from visualization.display_correlation import (
    display_species_domain_heatmap, display_species_domain_heatmap_with_features
)
from visualization.display_species_correlation import display_heatmap_speciesxspecies
from machine_learning.clustering import clustering, clustering_get_groups
from machine_learning.anomaly_detection import anomaly_detection
from machine_learning.dimensionality_reduction import dimensionality_reduction
from machine_learning.feature_engineering import feature_engineering
from machine_learning.data_loading import load_data
from orthology.ortho import generate_orthoxml, visualize_orthologs_multiple_layouts

# Constants
SPECIES_LIST_PATH = "data/list.2"
BLAST_FILE_PATH = "data/Sequences-218-annot.Query.blastp"
OUTPUT_DIR = "output"
TREE_FILE_PATH = f"{OUTPUT_DIR}/species_tree_approx.nw"
CORRELATION_MATRIX_PATH = f"{OUTPUT_DIR}/correlation_matrix.csv"
FEATURE_MATRIX_PATH = f"{OUTPUT_DIR}/feature_matrix.csv"
DOMAIN_CORRELATION_MATRIX_PATH = f"{OUTPUT_DIR}/domain_correlation_matrix.csv"
ORTHOXML_FILE_PATH = f"{OUTPUT_DIR}/orthologs.xml"
DEFAULT_TREE_DEPTH = 64

def construct_tree_command():
    species_df = load_species_data(SPECIES_LIST_PATH)
    representative_species, lower_triangle_matrix = approximate_distance_matrix(species_df)
    construct_tree(representative_species, lower_triangle_matrix)

def display_tree_command():
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TREE_DEPTH
    display_tree(TREE_FILE_PATH, max_depth=depth)

def display_heatmap_spxdm_command():
    run_heatmap_app(BLAST_FILE_PATH)
    
def all_vs_all_command():
    utilize_mcl_onNxN(find_true_positives(CORRELATION_MATRIX_PATH))
    
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

def ml_command():
    correlation_matrix = load_data(CORRELATION_MATRIX_PATH)
    clustering(correlation_matrix=correlation_matrix, n_clusters=3)
    dimensionality_reduction(correlation_matrix)
    anomaly_detection(correlation_matrix)
    feature_engineering(correlation_matrix)

def ortho_command():
    correlation_matrix = load_data(DOMAIN_CORRELATION_MATRIX_PATH)
    groups = clustering_get_groups(correlation_matrix)
    species_data = pd.DataFrame({
        "species_id": range(1, len(correlation_matrix.index) + 1),
        "species_name": correlation_matrix.index
    })
    generate_orthoxml(species_data, groups, output_file=ORTHOXML_FILE_PATH)

def vis_ortho_command():
    visualize_orthologs_multiple_layouts(ORTHOXML_FILE_PATH)

COMMANDS = {
    "--construct_tree": construct_tree_command,
    "--display_tree": display_tree_command,
    "--display_heatmap_spxdm": display_heatmap_spxdm_command,
    "--analyze": analyze_command,
    "--display_cor": display_cor_command,
    "--display_cor_features": display_cor_features_command,
    "--display_heatmap_spxsp": display_heatmap_spxsp_command,
    "--ml": ml_command,
    "--ortho": ortho_command,
    "--vis_ortho": vis_ortho_command,
    "--all_vs_all": all_vs_all_command
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
