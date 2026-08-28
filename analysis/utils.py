from config import SPECIES_SEGMENTS as _SPECIES_SEGMENTS

# Number of leading dash-delimited segments that identify a species/strain in a
# BLAST SubjectID, e.g. "UP000005640-00009606-Homo_sapi-22-001536-E-013170"
# -> "UP000005640-00009606-Homo_sapi-22".
SPECIES_SEGMENTS = _SPECIES_SEGMENTS


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

