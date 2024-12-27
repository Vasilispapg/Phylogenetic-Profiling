import re

def extract_species(subject_id):
    # Split the string by a common delimiter (e.g., '-')
    parts = subject_id.split('-')
    # Recombine parts up to the segment containing the numeric sequence
    for i, part in enumerate(parts):
        if any(char.isdigit() for char in part):  # Stop at the first part containing digits
            return '-'.join(parts[:4])
    return subject_id  # Fallback: return the original string if no digits found

def extract_partial_species(subject_id):
    """
    Extracts the species identifier up to the E-group.
    For example, 'UP000002254-00009615-Cani_lupu-22-001996-E-009974' -> 'UP000002254-00009615-Cani_lupu-22-001996-E-'
    """
    pattern = r'(.*?-\w+-\w+-\w+-[A-Z])'
    match = re.match(pattern, subject_id)
    return match.group(1) if match else subject_id  # Return the truncated ID or original
