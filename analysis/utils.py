import re

# Number of leading dash-delimited segments that identify a species/strain in a
# BLAST SubjectID, e.g. "UP000005640-00009606-Homo_sapi-22-001536-E-013170"
# -> "UP000005640-00009606-Homo_sapi-22".
SPECIES_SEGMENTS = 4


def extract_species(subject_id, num_segments=SPECIES_SEGMENTS):
    """
    Canonical species/strain key for a BLAST SubjectID.

    Returns the first ``num_segments`` dash-delimited segments. This is the
    single source of truth used by BOTH the correlation matrix and the feature
    matrix so their row labels stay consistent.

    Edge cases:
        - non-string / empty input  -> returned unchanged
        - fewer than ``num_segments`` segments -> full id returned
    """
    if not isinstance(subject_id, str) or not subject_id:
        return subject_id
    parts = subject_id.split('-')
    if len(parts) < num_segments:
        return subject_id
    return '-'.join(parts[:num_segments])


def extract_partial_species(subject_id):
    """
    Extract the species identifier up to the single-letter E-group, e.g.
    'UP000002254-00009615-Cani_lupu-22-001996-E-009974'
    -> 'UP000002254-00009615-Cani_lupu-22-001996-E'.

    Falls back to the original id when the pattern does not match.
    """
    if not isinstance(subject_id, str) or not subject_id:
        return subject_id
    match = re.match(r'(.*?-\w+-\w+-\w+-[A-Z])', subject_id)
    return match.group(1) if match else subject_id
