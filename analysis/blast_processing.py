import pandas as pd

from .utils import extract_species

def load_blast_data(protein_domain_path):
    """
    Load and process BLAST output data.

    Parameters:
    - protein_domain_path (str): Path to the BLAST output file.

    Returns:
    - pd.DataFrame: A DataFrame with the following columns:
        - QueryID: ID of the query sequence.
        - SpeciesCode: Extracted species code from the subject sequence ID.
        - PercentIdentity: Percentage of identical positions in the alignment.
        - EValue: Expectation value of the alignment.
    """
    try:
        # Define the columns to load and their names
        columns_to_load = [0, 1, 2, 10]  # BLAST columns: qseqid, sseqid, pident, evalue
        column_names = ['QueryID', 'SubjectID', 'PercentIdentity', 'EValue']
        
        # Load the specified columns from the BLAST file
        blast_df = pd.read_csv(
            protein_domain_path,
            sep='\t',
            header=None,
            usecols=columns_to_load,
            names=column_names
        )

        # Extract the canonical species key (shared with the matrix builders).
        blast_df['SpeciesCode'] = blast_df['SubjectID'].apply(extract_species)
        # Return the relevant columns
        return blast_df[['QueryID', 'SpeciesCode', 'PercentIdentity', 'EValue']]

    except Exception as e:
        print(f"Error loading BLAST data: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on failure
