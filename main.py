import sys
import pandas as pd
from tree_construction.construct_tree import compute_distance_matrix, construct_tree
from tree_construction.display_tree import display_tree
from analysis.matrix_operations import create_correlation_matrix, create_feature_matrix
from analysis.clustering_analysis import cluster_domains, domain_jaccard, validate_clusters
from visualization.display_correlation import (
    display_species_domain_heatmap, display_species_domain_heatmap_with_features
)
from visualization.display_species_correlation import display_heatmap_speciesxspecies

# Constants
BLAST_FILE_PATH = "data/Sequences-218-annot.Query.blastp"
OUTPUT_DIR = "output"
TREE_FILE_PATH = f"{OUTPUT_DIR}/species_tree_approx.nw"
CORRELATION_MATRIX_PATH = f"{OUTPUT_DIR}/correlation_matrix.csv"
FEATURE_MATRIX_PATH = f"{OUTPUT_DIR}/feature_matrix.csv"
DEFAULT_TREE_DEPTH = 64

def construct_tree_command():
    # Distances are derived from the species x domain presence/absence profile,
    # so the correlation matrix must be built first (run --analyze).
    species, lower_triangle_matrix = compute_distance_matrix(CORRELATION_MATRIX_PATH)
    construct_tree(species, lower_triangle_matrix)

def display_tree_command():
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TREE_DEPTH
    display_tree(TREE_FILE_PATH, max_depth=depth)
    
def all_vs_all_command():
    cluster_domains(CORRELATION_MATRIX_PATH, run_dash=True)

def validate_clusters_command():
    # Run domain clustering and print the validation report (no UI).
    import pandas as pd
    import networkx as nx
    from analysis.clustering_analysis import build_domain_graph, DEFAULT_THRESHOLD, DEFAULT_INFLATION
    import markov_clustering as mc
    from scipy.sparse import csr_matrix

    corr_df = pd.read_csv(CORRELATION_MATRIX_PATH, index_col=0)
    domains, J = domain_jaccard(corr_df)
    graph = build_domain_graph(domains, J, DEFAULT_THRESHOLD)
    adj = csr_matrix(nx.to_scipy_sparse_array(graph, nodelist=domains, weight="weight"))
    clusters = mc.get_clusters(mc.run_mcl(adj, inflation=DEFAULT_INFLATION))
    report = validate_clusters(graph, clusters, domains)
    print("\n=== Cluster validation report ===")
    for k, v in report.items():
        print(f"  {k}: {v}")

def analyze_command():
    create_correlation_matrix(BLAST_FILE_PATH)
    create_feature_matrix(BLAST_FILE_PATH)

def display_cor_command():
    display_species_domain_heatmap(CORRELATION_MATRIX_PATH)

def display_cor_features_command():
    display_species_domain_heatmap_with_features(FEATURE_MATRIX_PATH)

def display_heatmap_spxsp_command():
    display_heatmap_speciesxspecies(CORRELATION_MATRIX_PATH)

COMMANDS = {
    "--construct_tree": construct_tree_command,
    "--display_tree": display_tree_command,
    "--analyze": analyze_command,
    "--display_cor": display_cor_command,
    "--display_cor_features": display_cor_features_command,
    "--display_heatmap_spxsp": display_heatmap_spxsp_command,
    "--all_vs_all": all_vs_all_command,
    "--validate_clusters": validate_clusters_command,
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