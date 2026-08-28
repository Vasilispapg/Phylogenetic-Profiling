"""
What an upload has to prove.

The extension is a hint; these are the checks that actually decide. Nothing here
executes an upload — the point of the module is that a file which cannot be
parsed as the format it claims never reaches a parser at all.
"""
import io

import pytest

from analysis import upload_guard as ug


class FakeUpload:
    """The bits of werkzeug's FileStorage that stream_to_disk touches."""

    def __init__(self, data, mimetype="text/plain"):
        self.stream = io.BytesIO(data)
        self.mimetype = mimetype
        self.filename = "x.csv"


GOOD_BLAST = (
    "D1\tUP0-0-Aaa_aaa-22-1-E-1\t90.0\t100\t1\t0\t1\t100\t1\t100\t1e-30\t300\n"
).encode()
GOOD_MATRIX = b"Species,D1,D2\ns1,1,0\ns2,0,1\n"
GOOD_NEWICK = b"(a:0.1,(b:0.2,c:0.2):0.1);\n"


def save(tmp_path, data, kind, mimetype="text/plain"):
    dest = tmp_path / "out"
    return ug.stream_to_disk(FakeUpload(data, mimetype), kind, dest), dest


# --------------------------------------------------------------------------- #
# The happy paths
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind, data", [
    ("blast", GOOD_BLAST), ("matrix", GOOD_MATRIX), ("newick", GOOD_NEWICK),
])
def test_valid_files_are_kept(tmp_path, kind, data):
    size, dest = save(tmp_path, data, kind)
    assert size == len(data)
    assert dest.read_bytes() == data


def test_comments_and_blank_lines_are_skipped(tmp_path):
    save(tmp_path, b"# a comment\n\n" + GOOD_BLAST, "blast")


# --------------------------------------------------------------------------- #
# Size and shape
# --------------------------------------------------------------------------- #
def test_oversized_file_is_refused(tmp_path, monkeypatch):
    monkeypatch.setitem(ug.MAX_BYTES, "matrix", 1024)
    with pytest.raises(ug.RejectedUpload, match="larger than"):
        save(tmp_path, b"Species,D1\n" + b"s,1\n" * 500, "matrix")


def test_empty_file_is_refused(tmp_path):
    with pytest.raises(ug.RejectedUpload, match="empty"):
        save(tmp_path, b"", "matrix")


def test_one_enormous_line_is_refused(tmp_path, monkeypatch):
    """A single huge line is not a record format; it is a way to exhaust memory."""
    monkeypatch.setattr(ug, "MAX_LINE_BYTES", 2048)
    with pytest.raises(ug.RejectedUpload, match="single line"):
        save(tmp_path, b"Species,D1\n" + b"x" * 9000 + b"\n", "matrix")


def test_a_long_line_split_across_chunks_is_still_caught(tmp_path, monkeypatch):
    monkeypatch.setattr(ug, "MAX_LINE_BYTES", 2048)
    monkeypatch.setattr(ug, "CHUNK", 512)
    with pytest.raises(ug.RejectedUpload, match="single line"):
        save(tmp_path, b"Species,D1\n" + b"x" * 9000 + b"\n", "matrix")


# --------------------------------------------------------------------------- #
# Type: what it is, not what it is called
# --------------------------------------------------------------------------- #
def test_binary_content_is_refused(tmp_path):
    png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00"
    with pytest.raises(ug.RejectedUpload, match="binary"):
        save(tmp_path, png, "matrix")


def test_an_archive_content_type_is_refused(tmp_path):
    with pytest.raises(ug.RejectedUpload, match="not a text format"):
        save(tmp_path, GOOD_MATRIX, "matrix", mimetype="application/zip")


def test_an_image_content_type_is_refused(tmp_path):
    with pytest.raises(ug.RejectedUpload, match="not a text format"):
        save(tmp_path, GOOD_MATRIX, "matrix", mimetype="image/png")


# --------------------------------------------------------------------------- #
# Format: the contents have to match the claim
# --------------------------------------------------------------------------- #
def test_a_csv_pretending_to_be_blast_is_refused(tmp_path):
    with pytest.raises(ug.RejectedUpload, match="12 tab-separated"):
        save(tmp_path, b"q,subject,90.0,100\n", "blast")


def test_blast_with_a_non_numeric_evalue_is_refused(tmp_path):
    bad = "D1\tS1\t90.0\t100\t1\t0\t1\t100\t1\t100\tnot-a-number\t300\n".encode()
    with pytest.raises(ug.RejectedUpload, match="e-value"):
        save(tmp_path, bad, "blast")


def test_a_matrix_with_no_data_rows_is_refused(tmp_path):
    with pytest.raises(ug.RejectedUpload, match="header row"):
        save(tmp_path, b"Species,D1,D2\n", "matrix")


def test_a_single_column_matrix_is_refused(tmp_path):
    with pytest.raises(ug.RejectedUpload, match="species column"):
        save(tmp_path, b"Species\ns1\n", "matrix")


def test_prose_is_not_a_newick_tree(tmp_path):
    with pytest.raises(ug.RejectedUpload, match="Newick"):
        save(tmp_path, b"this is not a tree at all\n", "newick")


def test_unbalanced_newick_is_refused(tmp_path):
    with pytest.raises(ug.RejectedUpload, match="[Uu]nbalanced"):
        save(tmp_path, b"((a,b);\n", "newick")


def test_unterminated_newick_is_refused(tmp_path):
    with pytest.raises(ug.RejectedUpload, match="end with"):
        save(tmp_path, b"(a,b)\n", "newick")


def test_deeply_nested_newick_is_refused(tmp_path, monkeypatch):
    """Deep nesting is how you blow up a recursive parser."""
    monkeypatch.setattr(ug, "MAX_NEWICK_DEPTH", 50)
    bomb = b"(" * 500 + b"a" + b")" * 500 + b";"
    with pytest.raises(ug.RejectedUpload, match="nested"):
        save(tmp_path, bomb, "newick")


# --------------------------------------------------------------------------- #
# A rejected upload must leave nothing behind
# --------------------------------------------------------------------------- #
def test_a_rejected_upload_leaves_no_files(tmp_path):
    with pytest.raises(ug.RejectedUpload):
        save(tmp_path, b"nope", "newick")
    assert list(tmp_path.iterdir()) == []
