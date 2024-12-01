def extract_species(subject_id):
    # Split the string by a common delimiter (e.g., '-')
    parts = subject_id.split('-')
    # Recombine parts up to the segment containing the numeric sequence
    for i, part in enumerate(parts):
        if any(char.isdigit() for char in part):  # Stop at the first part containing digits
            return '-'.join(parts[:4])
    return subject_id  # Fallback: return the original string if no digits found