"""
Server-side matrix reading.

This replaces what the browser used to do with PapaParse plus a JSON.parse per
cell, so the edge cases that used to be covered in matrix.test.js are covered
here instead -- including the fast/slow extraction paths agreeing.
"""
import json

import numpy as np
import pytest

from analysis import matrix_io


def write(tmp_path, text, name="m.csv"):
    p = tmp_path / name
    p.write_text(text)
    return p


def feature_csv(cells):
    """A feature matrix with the same JSON layout create_feature_matrix writes."""
    header = "Species," + ",".join(f"D{j}" for j in range(len(cells[0])))
    lines = [header]
    for i, row in enumerate(cells):
        quoted = ",".join('"' + json.dumps(c).replace('"', '""') + '"' for c in row)
        lines.append(f"s{i},{quoted}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Numeric matrices
# --------------------------------------------------------------------------- #
def test_numeric_matrix(tmp_path):
    path = write(tmp_path, "Species,D1,D2\ns1,1,0\ns2,2,3\n")
    rows, cols, features, data = matrix_io.planes(path)
    assert rows == ["s1", "s2"] and cols == ["D1", "D2"]
    assert features == ["value"]
    assert data["value"].tolist() == [[1.0, 0.0], [2.0, 3.0]]


def test_blank_and_non_numeric_cells_become_zero(tmp_path):
    path = write(tmp_path, "Species,D1,D2\ns1,,x\n")
    _rows, _cols, _f, data = matrix_io.planes(path)
    assert data["value"].tolist() == [[0.0, 0.0]]


def test_ragged_rows_do_not_produce_nan(tmp_path):
    path = write(tmp_path, "Species,D1,D2\ns1,1\ns2,3,4\n")
    _rows, _cols, _f, data = matrix_io.planes(path)
    assert np.isfinite(data["value"]).all()


def test_empty_matrix_is_rejected(tmp_path):
    with pytest.raises(matrix_io.MatrixError):
        matrix_io.planes(write(tmp_path, "Species\n"))


def test_oversized_matrix_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(matrix_io, "MAX_CELLS", 3)
    path = write(tmp_path, "Species,D1,D2\ns1,1,2\ns2,3,4\n")
    with pytest.raises(matrix_io.MatrixError, match="limit"):
        matrix_io.planes(path)


# --------------------------------------------------------------------------- #
# Feature matrices (JSON cells with embedded commas)
# --------------------------------------------------------------------------- #
FEATURE_CELLS = [
    [{"num_hits": 3, "mean_bitscore": 300.5}, {"num_hits": 0, "mean_bitscore": 0}],
    [{"num_hits": 1, "mean_bitscore": 120.0}, {"num_hits": 2, "mean_bitscore": 240.25}],
]


def test_feature_matrix_is_detected_and_read(tmp_path):
    path = write(tmp_path, feature_csv(FEATURE_CELLS))
    rows, cols, features, data = matrix_io.planes(path)
    assert rows == ["s0", "s1"] and cols == ["D0", "D1"]
    assert features == ["num_hits", "mean_bitscore"]
    assert data["num_hits"].tolist() == [[3, 0], [1, 2]]
    assert data["mean_bitscore"].tolist() == [[300.5, 0], [120.0, 240.25]]


def test_describe_reports_metrics_without_values(tmp_path):
    meta = matrix_io.describe(write(tmp_path, feature_csv(FEATURE_CELLS)))
    assert meta["kind"] == "feature"
    assert meta["features"] == ["num_hits", "mean_bitscore"]
    assert "data" not in meta


def test_selecting_one_metric(tmp_path):
    path = write(tmp_path, feature_csv(FEATURE_CELLS))
    _rows, _cols, features, data = matrix_io.planes(path, ["mean_bitscore"])
    assert list(data) == ["mean_bitscore"]
    assert features == ["num_hits", "mean_bitscore"]     # all of them are reported


def test_unknown_metric_falls_back_to_the_first(tmp_path):
    path = write(tmp_path, feature_csv(FEATURE_CELLS))
    _rows, _cols, _f, data = matrix_io.planes(path, ["nope"])
    assert list(data) == ["num_hits"]


@pytest.mark.parametrize("values", [
    [[{"m": 1e-30}, {"m": 0}], [{"m": -2.5}, {"m": 1234567.0}]],
    [[{"m": 0}, {"m": 0}], [{"m": 0}, {"m": 0}]],
])
def test_fast_and_slow_extraction_agree(tmp_path, values):
    """The vectorised regex must match the json.loads reference exactly."""
    import pandas as pd
    path = write(tmp_path, feature_csv(values))
    df = pd.read_csv(path, index_col=0)
    fast = matrix_io._extract_many(df, ["m"])["m"]
    slow = matrix_io._extract_json(df, ["m"])["m"]
    assert np.allclose(fast, slow)


def test_extraction_falls_back_when_the_pattern_does_not_fit(tmp_path):
    """A cell holding the metric as a non-number must not silently become 0."""
    import pandas as pd
    path = write(tmp_path, 'Species,D0\ns0,"{""m"": ""not-a-number""}"\n')
    df = pd.read_csv(path, index_col=0)
    assert matrix_io._extract_regex(df, "m") is None      # detected, not guessed
