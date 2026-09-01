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
