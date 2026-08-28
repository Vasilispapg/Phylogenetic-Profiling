"""
What an upload has to prove before we keep it.

Nothing here ever executes what was uploaded — the files are only ever handed to
pandas and Bio.Phylo as data. The risks that remain are resource ones: a file
far larger than it claims, a single line big enough to exhaust memory when
parsed, a binary blob dressed up with a .csv extension, or a Newick string
nested deeply enough to blow a parser's stack. Each of those is checked here,
while the upload streams to disk, so a bad file never lands whole and is never
read into memory to be judged.

The extension is a hint, not evidence. Every kind is additionally *sniffed*:
the first lines have to look like the format the extension claims.
"""
import logging
import os
import re
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

# Per-kind ceilings, below the global MAX_CONTENT_LENGTH. A Newick tree for
# thousands of taxa is still small; matrices and BLAST output are not.
MAX_BYTES = {
    "blast": 64 * 1024 * 1024,
    "matrix": 64 * 1024 * 1024,
    "newick": 8 * 1024 * 1024,
}
# A line longer than this is not a record, it is an attempt to exhaust memory in
# whatever parses it. Real BLAST and CSV lines are a few hundred bytes.
MAX_LINE_BYTES = 1 * 1024 * 1024
# Deeply nested parentheses are how you blow up a recursive Newick parser.
MAX_NEWICK_DEPTH = 10_000
SNIFF_BYTES = 128 * 1024
CHUNK = 512 * 1024

# Declared content types we will accept. A browser sends wildly inconsistent
# values for CSV and text, so this only rejects the obviously wrong ones
# (archives, executables, images) rather than acting as the real check.
FORBIDDEN_TYPES = re.compile(
    r"^(application/(zip|gzip|x-tar|x-7z|x-rar|java-archive|x-msdownload|"
    r"x-executable|x-sharedlib|octet-stream(?!$))|image/|audio/|video/)",
    re.I,
)


class RejectedUpload(ValueError):
    """The upload is not something we are willing to keep."""


def _fail(message):
    raise RejectedUpload(message)


def stream_to_disk(storage, kind, destination):
    """
    Copy an upload to ``destination``, rejecting it the moment it misbehaves.

    Returns the number of bytes written. Raises :class:`RejectedUpload` with a
    message meant for the person who uploaded the file.
    """
    limit = MAX_BYTES[kind]
    declared = (storage.mimetype or "").strip()
    if declared and FORBIDDEN_TYPES.match(declared):
        _fail(f"{declared} is not a text format; upload the plain text file itself.")

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(dir=destination.parent, suffix=".part")
    temp_path = Path(temp_path)

    total = 0
    head = bytearray()
    line_length = 0
    try:
        with os.fdopen(handle, "wb") as out:
            while True:
                chunk = storage.stream.read(CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    _fail(f"File is larger than the {limit // (1024 * 1024)} MB limit "
                          f"for a {kind} file.")
                if b"\0" in chunk:
                    _fail("File contains binary data; this tool only reads text formats.")

                line_length = _check_line_lengths(chunk, line_length)
                if len(head) < SNIFF_BYTES:
                    head.extend(chunk[: SNIFF_BYTES - len(head)])
                out.write(chunk)

        if total == 0:
            _fail("File is empty.")
        text = _decode(bytes(head))
        SNIFFERS[kind](text)
        temp_path.replace(destination)
        return total
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _check_line_lengths(chunk, carried):
    """Track line length across chunk boundaries; reject a line that is absurd."""
    parts = chunk.split(b"\n")
    if len(parts) == 1:
        carried += len(parts[0])
        if carried > MAX_LINE_BYTES:
            _fail("File contains a single line over 1 MB; that is not a record-based format.")
        return carried
    if carried + len(parts[0]) > MAX_LINE_BYTES:
        _fail("File contains a single line over 1 MB; that is not a record-based format.")
    for middle in parts[1:-1]:
        if len(middle) > MAX_LINE_BYTES:
            _fail("File contains a single line over 1 MB; that is not a record-based format.")
    return len(parts[-1])


def _decode(raw):
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # A truncated multi-byte character at the sniff boundary is fine; real
        # binary is not, and the NUL check above has already caught most of it.
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:                                   # pragma: no cover
            _fail("File is not valid UTF-8 text.")


def _first_records(text, count=5):
    """The first few lines that carry data, ignoring blanks and comments."""
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append(line)
        if len(out) == count:
            break
    return out


def sniff_blast(text):
    """BLAST tabular: tab-separated, at least 12 fields, numbers where numbers go."""
    records = _first_records(text)
    if not records:
        _fail("File has no data lines.")
    first = records[0]
    fields = first.split("\t")
    if len(fields) < 12:
        _fail(f"Expected BLAST tabular output (-outfmt 6): 12 tab-separated columns, "
              f"found {len(fields)} on the first line. "
              f"A comma-separated file is not accepted here.")
    for index, label in ((2, "percent identity"), (10, "e-value"), (11, "bit score")):
        try:
            float(fields[index])
        except ValueError:
            _fail(f"Column {index + 1} should be the {label}, but it reads "
                  f"{fields[index][:32]!r}. Is this -outfmt 6?")


def sniff_matrix(text):
    """A matrix: a header plus data rows, at least one label column and one value."""
    records = _first_records(text)
    if len(records) < 2:
        _fail("Expected a header row and at least one data row.")
    header, first_row = records[0], records[1]
    delimiter = "\t" if header.count("\t") > header.count(",") else ","
    columns = len(header.split(delimiter))
    if columns < 2:
        _fail("Expected a species column plus at least one domain column.")
    if len(first_row.split(delimiter)) < 2:
        _fail("The first data row does not use the same delimiter as the header.")


def sniff_newick(text):
    """Newick: balanced parentheses, terminated, and not nested absurdly deep."""
    stripped = text.strip()
    if "(" not in stripped:
        _fail("Expected a Newick tree: nested parentheses ending in ';'.")
    depth = 0
    deepest = 0
    for char in stripped:
        if char == "(":
            depth += 1
            deepest = max(deepest, depth)
            if deepest > MAX_NEWICK_DEPTH:
                _fail(f"Tree is nested more than {MAX_NEWICK_DEPTH} levels deep.")
        elif char == ")":
            depth -= 1
            if depth < 0:
                _fail("Unbalanced parentheses in the Newick tree.")
    # The head may be a truncated prefix of a large tree, so only a complete
    # read can be checked for balance and termination.
    if len(stripped) < SNIFF_BYTES - 1:
        if depth != 0:
            _fail("Unbalanced parentheses in the Newick tree.")
        if not stripped.endswith(";"):
            _fail("A Newick tree has to end with ';'.")


SNIFFERS = {"blast": sniff_blast, "matrix": sniff_matrix, "newick": sniff_newick}
