import sys
import pandas as pd
from tree_construction.construct_tree import load_species_data, approximate_distance_matrix, construct_tree
from tree_construction.display_tree import display_tree
from analysis.analyze_genomes import load_blast_data, create_correlation_matrix, create_similarity_matrix, run_heatmap_app, find_true_positives, utilize_mcl_onNxN
from visualization.display_correlation import display_species_domain_heatmap
from visualization.display_species_correlation import display_heatmap_speciesxspecies
from machine_learning.clustering import clustering,clustering_get_groups
from machine_learning.anomaly_detection import anomaly_detection
from machine_learning.dimensionality_reduction import dimensionality_reduction
from machine_learning.feature_engineering import feature_engineering
from machine_learning.data_loading import load_data
from orthology.ortho import generate_orthoxml, visualize_orthologs_multiple_layouts


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py [construct_tree|display_cor|display_tree|analyze|display_heatmap_spxdm|display_heatmap_spxsp|ml|ortho|vis_ortho]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "--construct_tree":
        species_list_path = "data/list.2"
        species_df = load_species_data(species_list_path)
        representative_species, lower_triangle_matrix = approximate_distance_matrix(species_df)
        construct_tree(representative_species, lower_triangle_matrix)
    elif command == "--display_tree":
        depth = int(sys.argv[2]) if len(sys.argv) > 2 else 64  # Default to 4 if no depth specified
        display_tree("output/species_tree_approx.nw",max_depth=depth)
    elif command == "--display_heatmap_spxdm":
        blast_file_path = "data/Sequences-218-annot.Query.blastp"
        run_heatmap_app(blast_file_path)
    elif command == "--analyze":
        protein_domain_path = "data/Sequences-218-annot.Query.blastp"
        create_correlation_matrix(protein_domain_path)
        # create_similarity_matrix(load_blast_data(protein_domain_path))
        utilize_mcl_onNxN(find_true_positives("output/correlation_matrix.csv"))
    elif command == "--display_cor":
        display_species_domain_heatmap("output/correlation_matrix.csv")    
    elif command == "--display_heatmap_spxsp":
        display_heatmap_speciesxspecies("output/correlation_matrix.csv")
        display_heatmap_speciesxspecies("output/domain_correlation_matrix.csv")
    elif command == "--ml":
        correlation_matrix = load_data("output/domain_correlation_matrix.csv")
        # Perform Clustering
        cluster_labels = clustering(correlation_matrix=correlation_matrix,n_clusters=9)
        # Perform Dimensionality Reduction
        reduced_data = dimensionality_reduction(correlation_matrix)

        # Perform Anomaly Detection
        outliers = anomaly_detection(correlation_matrix)

        # Perform Feature Engineering
        engineered_features = feature_engineering(correlation_matrix)
    elif command == '--ortho':
        correlation_matrix = load_data("output/domain_correlation_matrix.csv")

        groups = clustering_get_groups(correlation_matrix)
        
        # Load species data for OrthoXML generation
        species_data = pd.DataFrame({
            "species_id": range(1, len(correlation_matrix.index) + 1),
            "species_name": correlation_matrix.index
        })
        
        # Generate OrthoXML with the groups
        generate_orthoxml(species_data, groups, output_file="output/orthologs.xml")
    elif command =='--vis_ortho':
        visualize_orthologs_multiple_layouts('output/orthologs.xml')
    else:
        print("Invalid command. Use 'construct', 'display', or 'analyze' or 'heatmap_spxsp' or 'machine_learning' or 'ortho' or 'vis_ortho'")

if __name__ == "__main__":
    main()
