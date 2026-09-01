"""
The CLI's argument surface is a contract, so it is pinned here.

main.py used to read ``sys.argv`` by position and keep every path in a module
constant. Now each command parses its own options and the paths are arguments,
which means two things can break silently: the invocations the README documents
(``--analyze``, ``--construct_tree upgma``, ``--display_tree 12``) and the
routing of ``-i``/``-o`` to the right function argument. Both are asserted below.

What those functions *compute* is tests/test_pipeline.py's job, so here they are
replaced with recorders -- these tests stay fast and touch no data.
"""
import argparse
import json
from pathlib import Path

import pytest

import config
import main


@pytest.fixture
def calls(monkeypatch):
    """Swap every pipeline entry point for a recorder; return what was called."""
    recorded = {}

    def recorder(name, result=None):
        def record(*args, **kwargs):
            recorded[name] = (args, kwargs)
            return result
        return record

    for name in ("create_correlation_matrix", "create_feature_matrix",
                 "construct_tree", "display_tree", "cluster_domains",
                 "display_species_domain_heatmap",
                 "display_species_domain_heatmap_with_features",
                 "display_heatmap_speciesxspecies"):
        monkeypatch.setattr(main, name, recorder(name))

    # These two have to hand something back to their caller.
    monkeypatch.setattr(main, "compute_square_distances",
                        recorder("compute_square_distances", (["s1", "s2"], "distances")))
    import analysis.clustering_analysis as clustering
    monkeypatch.setattr(clustering, "cluster_payload",
                        recorder("cluster_payload", {"metrics": {"n_clusters": 2}}))
    return recorded


def _file(tmp_path, name):
    """An input file that exists (the commands refuse to run without one)."""
    path = tmp_path / name
    path.write_text("x")
    return path


# --------------------------------------------------------------------------- #
# paths are arguments
# --------------------------------------------------------------------------- #
def test_analyze_takes_an_input_file_and_an_output_directory(calls, tmp_path):
    blast = _file(tmp_path, "mine.blastp")
    out = tmp_path / "runs" / "mine"          # deliberately does not exist yet

    main.main(["--analyze", "-i", str(blast), "-o", str(out)])

    assert calls["create_correlation_matrix"][0] == (str(blast), str(out / "correlation_matrix.csv"))
    assert calls["create_feature_matrix"][0] == (str(blast), str(out / "feature_matrix.csv"))
    assert out.is_dir()


def test_analyze_defaults_to_the_bundled_dataset(calls):
    """No flags == what the command did before it had any."""
    main.main(["--analyze"])

    blast, correlation = calls["create_correlation_matrix"][0]
    assert blast == str(config.BASE / "data" / "Sequences-218-annot.Query.blastp")
    assert Path(blast).is_file()              # the documented default really is there
    assert correlation == str(config.OUTPUT_DIR / "correlation_matrix.csv")


def test_construct_tree_routes_both_paths(calls, tmp_path):
    matrix = _file(tmp_path, "correlation_matrix.csv")
    out = tmp_path / "trees" / "mine.nw"

    main.main(["--construct_tree", "-i", str(matrix), "-o", str(out)])

    assert calls["compute_square_distances"][0] == (str(matrix),)
    species, distances = calls["construct_tree"][0]
    assert (species, distances) == (["s1", "s2"], "distances")
    assert calls["construct_tree"][1] == {"output_path": str(out), "method": "nj"}
    assert out.parent.is_dir()


@pytest.mark.parametrize("command, recorded", [
    ("--display_cor", "display_species_domain_heatmap"),
    ("--display_cor_features", "display_species_domain_heatmap_with_features"),
    ("--display_heatmap_spxsp", "display_heatmap_speciesxspecies"),
    ("--all_vs_all", "cluster_domains"),
])
def test_input_path_reaches_the_command(calls, tmp_path, command, recorded):
    path = _file(tmp_path, "in.csv")
    main.main([command, "-i", str(path)])
    assert calls[recorded][0][0] == str(path)


def test_validate_clusters_reports_on_the_given_matrix(calls, tmp_path, capsys):
    matrix = _file(tmp_path, "c.csv")

    main.main(["--validate_clusters", "-i", str(matrix)])

    assert calls["cluster_payload"][0] == (str(matrix),)
    assert "n_clusters: 2" in capsys.readouterr().out


@pytest.mark.parametrize("name", sorted(main.COMMANDS))
def test_every_command_accepts_an_input_path(name):
    parser = argparse.ArgumentParser()
    main.COMMANDS[name].add_arguments(parser)
    assert parser.parse_args(["-i", "~/matrix.csv"]).input == Path("~/matrix.csv").expanduser()


@pytest.mark.parametrize("name", sorted(main.COMMANDS))
def test_defaults_are_absolute(name):
    """Relative defaults would make a command mean different things per directory."""
    parser = argparse.ArgumentParser()
    main.COMMANDS[name].add_arguments(parser)
    defaults = parser.parse_args([])
    assert defaults.input.is_absolute()
    assert getattr(defaults, "output", Path("/")).is_absolute()


# --------------------------------------------------------------------------- #
# the invocations the README documents keep working
# --------------------------------------------------------------------------- #
def test_construct_tree_keeps_its_positional_method(calls, tmp_path):
    main.main(["--construct_tree", "upgma", "-i", str(_file(tmp_path, "c.csv"))])
    assert calls["construct_tree"][1]["method"] == "upgma"


def test_display_tree_keeps_its_positional_depth(calls, tmp_path):
    tree = _file(tmp_path, "t.nw")

    main.main(["--display_tree", "12", "-i", str(tree)])
    assert calls["display_tree"] == ((str(tree),), {"max_depth": 12})

    main.main(["--display_tree", "-i", str(tree)])
    assert calls["display_tree"][1] == {"max_depth": config.TREE_DISPLAY_DEPTH}


def test_command_names_work_with_and_without_the_dashes(calls, tmp_path):
    blast = _file(tmp_path, "mine.blastp")
    main.main(["analyze", "-i", str(blast), "-o", str(tmp_path / "out")])
    assert calls["create_correlation_matrix"][0][0] == str(blast)


# --------------------------------------------------------------------------- #
# failure modes: a sentence, not a traceback
# --------------------------------------------------------------------------- #
def test_a_missing_input_names_the_path_it_looked_for(calls, tmp_path):
    absent = tmp_path / "absent.csv"

    with pytest.raises(SystemExit) as exit_info:
        main.main(["--construct_tree", "-i", str(absent)])

    assert str(absent) in str(exit_info.value)
    assert "compute_square_distances" not in calls      # refused before doing work


def test_an_unknown_command_exits_with_the_command_list(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main.main(["--bogus"])

    assert exit_info.value.code == 1
    out = capsys.readouterr().out
    assert "Invalid command: --bogus" in out
    assert all(name in out for name in main.COMMANDS)


def test_an_unknown_tree_method_is_rejected_by_the_parser(calls, tmp_path):
    with pytest.raises(SystemExit) as exit_info:
        main.main(["--construct_tree", "wpgma", "-i", str(_file(tmp_path, "c.csv"))])

    assert exit_info.value.code == 2                    # argparse usage error
    assert "construct_tree" not in calls


def test_no_arguments_is_an_error_but_help_is_not(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main.main([])
    assert exit_info.value.code == 1

    main.main(["--help"])                               # returns, does not exit
    out = capsys.readouterr().out
    assert all(name in out for name in main.COMMANDS)


# --------------------------------------------------------------------------- #
# per-tool options: the knobs that used to need an env var or a code edit
# --------------------------------------------------------------------------- #
def test_analyze_passes_the_science_knobs_to_both_matrices(calls, tmp_path):
    blast = _file(tmp_path, "mine.blastp")

    main.main(["--analyze", "-i", str(blast), "-o", str(tmp_path / "out"),
               "--evalue", "1e-10", "--using-pi"])

    assert calls["create_correlation_matrix"][1] == {"using_pi": True, "evalue_threshold": 1e-10}
    # The feature matrix gets the same cutoff, or the two stop agreeing on
    # what "present" means -- the whole reason the filter lives in one place.
    assert calls["create_feature_matrix"][1] == {"evalue_threshold": 1e-10}


def test_evalue_none_keeps_every_hit(calls, tmp_path):
    main.main(["--analyze", "-i", str(_file(tmp_path, "b.blastp")),
               "-o", str(tmp_path / "out"), "--evalue", "none"])
    assert calls["create_correlation_matrix"][1]["evalue_threshold"] is None


def test_construct_tree_takes_a_profile_metric(calls, tmp_path):
    main.main(["--construct_tree", "-i", str(_file(tmp_path, "c.csv")), "--metric", "dice"])
    assert calls["compute_square_distances"][1] == {"metric": "dice"}


def test_an_unknown_profile_metric_is_rejected(calls, tmp_path):
    with pytest.raises(SystemExit) as exit_info:
        main.main(["--construct_tree", "-i", str(_file(tmp_path, "c.csv")),
                   "--metric", "euclidean"])
    assert exit_info.value.code == 2
    assert "compute_square_distances" not in calls


@pytest.mark.parametrize("command, recorded", [
    ("--all_vs_all", "cluster_domains"),
    ("--validate_clusters", "cluster_payload"),
])
def test_clustering_commands_take_threshold_and_inflation(calls, tmp_path, command, recorded):
    main.main([command, "-i", str(_file(tmp_path, "c.csv")),
               "--threshold", "0.6", "--inflation", "2.5"])
    kwargs = calls[recorded][1]
    assert kwargs["threshold"] == 0.6
    assert kwargs["inflation"] == 2.5


def test_clustering_defaults_come_from_config(calls, tmp_path):
    from analysis.clustering_analysis import DEFAULT_INFLATION, DEFAULT_THRESHOLD

    main.main(["--validate_clusters", "-i", str(_file(tmp_path, "c.csv"))])
    assert calls["cluster_payload"][1] == {"threshold": DEFAULT_THRESHOLD,
                                           "inflation": DEFAULT_INFLATION}


# --------------------------------------------------------------------------- #
# --embed: JSON out, plot optional
# --------------------------------------------------------------------------- #
MATRIX_CSV = ",D1,D2,D3,D4\nS1,1,0,1,0\nS2,1,0,1,0\nS3,0,1,0,1\n"


@pytest.fixture
def matrix(tmp_path):
    path = tmp_path / "correlation_matrix.csv"
    path.write_text(MATRIX_CSV)
    return path


def test_embed_writes_the_coordinates_as_json(matrix, tmp_path, capsys):
    out = tmp_path / "embeddings" / "domains.json"

    main.main(["--embed", "-i", str(matrix), "-o", str(out), "-k", "2"])

    result = json.loads(out.read_text())
    assert result["names"] == ["D1", "D2", "D3", "D4"]      # a point per column
    assert len(result["coords"]) == len(result["labels"]) == 4
    assert all(len(xy) == 2 for xy in result["coords"])
    assert (result["method"], result["axis"], result["k"]) == ("pca", "domains", 2)
    assert "projected with PCA" in capsys.readouterr().out


def test_embed_projects_species_when_asked(matrix, tmp_path):
    out = tmp_path / "species.json"
    main.main(["--embed", "-i", str(matrix), "-o", str(out), "--axis", "species", "-k", "2"])
    assert json.loads(out.read_text())["names"] == ["S1", "S2", "S3"]


def test_embed_is_reproducible(matrix, tmp_path):
    """
    Same matrix, same picture.

    scikit-learn picks the randomized SVD solver at these shapes, so an unseeded
    PCA moves the points on every run -- which would put the CLI and the web's
    cached answer at odds.
    """
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    for out in (first, second):
        main.main(["--embed", "-i", str(matrix), "-o", str(out)])
    assert json.loads(first.read_text()) == json.loads(second.read_text())


def test_embed_only_plots_when_asked(matrix, tmp_path, monkeypatch):
    import visualization.display_embedding as plotting
    shown = []
    monkeypatch.setattr(plotting, "display_embedding",
                        lambda *args, **kwargs: shown.append(kwargs))

    main.main(["--embed", "-i", str(matrix), "-o", str(tmp_path / "a.json")])
    assert shown == []

    main.main(["--embed", "-i", str(matrix), "-o", str(tmp_path / "b.json"),
               "--method", "tsne", "--show"])
    assert shown == [{"axis": "domains", "method": "tsne"}]


def test_embed_selects_a_feature_plane(matrix, tmp_path, monkeypatch):
    """A feature matrix holds several metrics per cell; --feature picks one."""
    from analysis import matrix_io
    seen = {}
    real_plane = matrix_io.plane

    def recording_plane(path, metric=None):
        seen["metric"] = metric
        return real_plane(path, metric)

    monkeypatch.setattr(matrix_io, "plane", recording_plane)

    main.main(["--embed", "-i", str(matrix), "-o", str(tmp_path / "a.json"),
               "--feature", "mean_bitscore"])
    assert seen["metric"] == "mean_bitscore"


def test_an_unknown_projection_is_rejected(matrix, tmp_path):
    with pytest.raises(SystemExit) as exit_info:
        main.main(["--embed", "-i", str(matrix), "--method", "umap"])
    assert exit_info.value.code == 2
