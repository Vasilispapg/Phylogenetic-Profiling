import pandas as pd
from dash import Dash, dcc, html
import plotly.graph_objects as go
import pdb

def load_blast_data(protein_domain_path):
    blast_df = pd.read_csv(protein_domain_path, sep='\t', header=None,
                           usecols=[0, 1, 2, 10],
                           names=['QueryID', 'SubjectID', 'PercentIdentity', 'EValue'])
    blast_df['SpeciesCode'] = blast_df['SubjectID'].str.split('-').str[2]
    return blast_df[['QueryID', 'SpeciesCode', 'PercentIdentity', 'EValue']]

def extract_species(subject_id):
    # Split the string by a common delimiter (e.g., '-')
    parts = subject_id.split('-')
    # Recombine parts up to the segment containing the numeric sequence
    for i, part in enumerate(parts):
        if any(char.isdigit() for char in part):  # Stop at the first part containing digits
            return '-'.join(parts[:4])
    return subject_id  # Fallback: return the original string if no digits found

def create_correlation_matrix(blast_file_path, output_path="output/correlation_matrix.csv"):
    """
    Parse the BLAST file and create a matrix where rows are species and columns are domains.

    Parameters:
    - blast_file_path (str): Path to the BLAST file.

    Returns:
    - pd.DataFrame: A DataFrame with species as rows and domains as columns.
    """

    # Read the BLAST file
    blast_df = pd.read_csv(
        blast_file_path,
        sep='\t',
        header=None,
        names=['QueryID', 'SubjectID', 'PercentIdentity', 'AlignmentLength', 'Mismatches', 'GapOpens',
               'QueryStart', 'QueryEnd', 'SubjectStart', 'SubjectEnd', 'EValue', 'BitScore']
    )
    # Extract species and domains
    blast_df['Domain'] = blast_df['QueryID']
    # Apply the extraction logic to the 'SubjectID' column
    blast_df['Species'] = blast_df['SubjectID'].apply(extract_species)
    # Pivot to create a matrix with species as rows and domains as columns
    heatmap_data = pd.pivot_table(
        blast_df,
        index='Species',
        columns='Domain',
        aggfunc='size',  # Count occurrences
        fill_value=0      # Fill absence with 0
    )
    # Calculate the correlation matrix
    heatmap_data.to_csv(output_path)
    print(f"Correlation matrix saved to {output_path}")
    
    return heatmap_data

def create_species_domain_heatmap(matrix):
    """
    Create a heatmap with species as rows and domains as columns.

    Parameters:
    - matrix (pd.DataFrame): The matrix with species as rows and domains as columns.

    Returns:
    - go.Figure: A Plotly figure object containing the heatmap.
    """
    
    heatmap = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            x=matrix.columns,
            y=matrix.index,
            colorscale="Viridis",
            colorbar={"title": "Percent Identity"}
        )
    )
    heatmap.update_layout(
        title="Species-Domain Heatmap",
        xaxis_title="Domains",
        yaxis_title="Species",
        height=800,
        width=1200,
    )
    return heatmap

def run_heatmap_app(blast_file_path):
    """
    Run a Dash app to display the interactive heatmap.

    Parameters:
    - blast_file_path (str): Path to the BLAST file.
    """
    # Parse the BLAST file to create the matrix
    matrix = create_correlation_matrix(blast_file_path)

    # Initialize the Dash app
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1("Species-Domain Heatmap"),
        dcc.Graph(
            id="heatmap",
            figure=create_species_domain_heatmap(matrix)
        )
    ])

    # Run the Dash app
    app.run_server(debug=True)
    
def find_true_positives(corr_matrix_path):
    
    # Load the correlation matrix
    corr_matrix = pd.read_csv(corr_matrix_path, index_col=0)
    
    
    return
    
def create_similarity_matrix(blast_df, output_path="output/domain_similarity_matrix.csv"):
    # Pivot to create a matrix where rows are species, columns are queries, and values are percent identity
    similarity_matrix = blast_df.pivot_table(
        index='SpeciesCode', columns='QueryID', values='PercentIdentity', fill_value=0
    )
    
    # Calculate pairwise correlation between species
    correlation_matrix = similarity_matrix.T.corr()  # Transpose to correlate species
    
    # Save the correlation matrix
    correlation_matrix.to_csv(output_path)
    print(f"Correlation matrix saved as {output_path}")
    
    return correlation_matrix