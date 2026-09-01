"""
CLI entry point: the same analysis pipeline the web API runs, headlessly.

Every command takes its input path on the command line (``-i/--input``) and
writes where you tell it (``-o/--output``); the defaults are the bundled dataset
and ``output/``, so the documented one-word invocations still work. Defaults are
absolute (derived from ``config.BASE``), so a command behaves the same whatever
directory it is run from -- the same reason config.py resolves its paths.

    python main.py --analyze -i data/mine.blastp -o runs/mine
    python main.py --construct_tree upgma -i runs/mine/correlation_matrix.csv \
                                          -o runs/mine/tree.nw
    python main.py --embed --method tsne --axis species --show

Beyond the paths, each command carries its own knobs -- the E-value cutoff, the
profile distance, the MCL threshold and inflation, the projection -- so anything
that used to require an environment variable or an edit is now a flag:

    python main.py <command> --help     # the options for one command
"""
import argparse
import json
import logging
import sys
from collections import namedtuple
from pathlib import Path

import config
from tree_construction.construct_tree import (
    PROFILE_METRICS, compute_square_distances, construct_tree
)
from tree_construction.display_tree import display_tree
from tree_construction.nj import METHODS
from analysis import matrix_io
from analysis.embedding import AXES, embed
from analysis.embedding import METHODS as EMBED_METHODS
from analysis.matrix_operations import create_correlation_matrix, create_feature_matrix
from analysis.clustering_analysis import (  # noqa: F401
    DEFAULT_INFLATION, DEFAULT_THRESHOLD, cluster_domains, domain_jaccard, validate_clusters
)
from visualization.display_correlation import (
    display_species_domain_heatmap, display_species_domain_heatmap_with_features
)
from visualization.display_species_correlation import display_heatmap_speciesxspecies

# Defaults only: every one of these can be overridden per run.
BLAST_FILE_PATH = config.BASE / "data" / "Sequences-218-annot.Query.blastp"
OUTPUT_DIR = config.OUTPUT_DIR
CORRELATION_MATRIX_PATH = OUTPUT_DIR / "correlation_matrix.csv"
FEATURE_MATRIX_PATH = OUTPUT_DIR / "feature_matrix.csv"
TREE_FILE_PATH = OUTPUT_DIR / "species_tree_approx.nw"
EMBEDDING_PATH = OUTPUT_DIR / "embedding.json"
DEFAULT_TREE_DEPTH = config.TREE_DISPLAY_DEPTH

# Written by --analyze into whatever directory it is pointed at, and the names
# the other commands expect to find there.
CORRELATION_MATRIX_NAME = "correlation_matrix.csv"
FEATURE_MATRIX_NAME = "feature_matrix.csv"


# --------------------------------------------------------------------------- #
# argument plumbing
# --------------------------------------------------------------------------- #
def _path(value):
    """A path argument, with ``~`` expanded (a shell would, argparse would not)."""
    return Path(value).expanduser()


def _require(path, what):
    """
    Fail with one sentence when an input is missing.

    Without this a mistyped path reaches pandas and comes back as a traceback,
    which says the same thing in twenty lines.
    """
    if not path.is_file():
        raise SystemExit(f"{what} not found: {path}\n"
                         f"Pass the right one with -i/--input.")
    return path


def _input(parser, default, help_text):
    parser.add_argument("-i", "--input", type=_path, default=default,
                        metavar="PATH", help=f"{help_text} (default: {default})")


def _output(parser, default, help_text):
    parser.add_argument("-o", "--output", type=_path, default=default,
                        metavar="PATH", help=f"{help_text} (default: {default})")


def _evalue(value):
    """An E-value cutoff, or ``none`` to count every reported hit."""
    if value.strip().lower() == "none":
        return None
    return float(value)


def _clustering(parser):
    """The two MCL knobs, shared by the commands that cluster domains."""
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, metavar="J",
                        help="minimum Jaccard similarity for a domain-domain edge "
                             f"(default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--inflation", type=float, default=DEFAULT_INFLATION, metavar="I",
                        help="MCL granularity; higher gives more, smaller clusters "
                             f"(default: {DEFAULT_INFLATION})")


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def analyze_args(parser):
    _input(parser, BLAST_FILE_PATH, "BLAST tabular file to analyse")
    _output(parser, OUTPUT_DIR,
            f"directory to write {CORRELATION_MATRIX_NAME} and {FEATURE_MATRIX_NAME} to")
    parser.add_argument("--evalue", type=_evalue, default=config.EVALUE_THRESHOLD,
                        metavar="E",
                        help="count a hit as present only at or below this E-value; "
                             f"'none' keeps every hit (default: {config.EVALUE_THRESHOLD})")
    parser.add_argument("--using-pi", action="store_true",
                        help="correlation cells are mean percent identity instead of hit "
                             "counts (written as correlation_matrix_pi.csv)")


def analyze_command(args):
    blast = _require(args.input, "BLAST file")
    args.output.mkdir(parents=True, exist_ok=True)
    # One cutoff for both matrices, so they keep agreeing on what "present" means.
    create_correlation_matrix(str(blast), str(args.output / CORRELATION_MATRIX_NAME),
                              using_pi=args.using_pi, evalue_threshold=args.evalue)
    create_feature_matrix(str(blast), str(args.output / FEATURE_MATRIX_NAME),
                          evalue_threshold=args.evalue)


def construct_tree_args(parser):
    parser.add_argument("method", nargs="?", default="nj", choices=sorted(METHODS),
                        help="tree-building method (default: nj)")
    _input(parser, CORRELATION_MATRIX_PATH, "species x domain matrix to build the tree from")
    _output(parser, TREE_FILE_PATH, "Newick file to write")
    parser.add_argument("--metric", default="jaccard", choices=PROFILE_METRICS,
                        help="distance between presence/absence profiles (default: jaccard)")


def construct_tree_command(args):
    # Distances are derived from the species x domain presence/absence profile,
    # so the correlation matrix must exist first (run --analyze).
    matrix = _require(args.input, "Correlation matrix")
    species, distances = compute_square_distances(str(matrix), metric=args.metric)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    construct_tree(species, distances, output_path=str(args.output), method=args.method)


def display_tree_args(parser):
    parser.add_argument("depth", nargs="?", type=int, default=DEFAULT_TREE_DEPTH,
                        help=f"levels to draw (default: {DEFAULT_TREE_DEPTH})")
    _input(parser, TREE_FILE_PATH, "Newick file to draw")


def display_tree_command(args):
    display_tree(str(_require(args.input, "Newick file")), max_depth=args.depth)


def all_vs_all_args(parser):
    _input(parser, CORRELATION_MATRIX_PATH, "correlation matrix to cluster")
    _clustering(parser)


def all_vs_all_command(args):
    cluster_domains(str(_require(args.input, "Correlation matrix")),
                    threshold=args.threshold, inflation=args.inflation, run_dash=True)


def validate_clusters_args(parser):
    _input(parser, CORRELATION_MATRIX_PATH, "correlation matrix to cluster")
    _clustering(parser)


def validate_clusters_command(args):
    # Run domain clustering and print the validation report (no UI). This is the
    # same cluster_payload() the web's background job calls.
    from analysis.clustering_analysis import cluster_payload

    matrix = _require(args.input, "Correlation matrix")
    report = cluster_payload(str(matrix), threshold=args.threshold,
                             inflation=args.inflation)["metrics"]
    print("\n=== Cluster validation report ===")
    for k, v in report.items():
        print(f"  {k}: {v}")


def embed_args(parser):
    _input(parser, CORRELATION_MATRIX_PATH, "matrix to project")
    _output(parser, EMBEDDING_PATH, "JSON file to write")
    parser.add_argument("--method", default="pca", choices=EMBED_METHODS,
                        help="projection (default: pca)")
    parser.add_argument("--axis", default="domains", choices=AXES,
                        help="what a point is: matrix columns or rows (default: domains)")
    parser.add_argument("-k", type=int, default=8, metavar="N",
                        help="KMeans clusters used to colour the points (default: 8)")
    parser.add_argument("--feature", metavar="NAME",
                        help="which plane of a feature matrix to project "
                             "(feature matrices only; default: the first)")
    parser.add_argument("--show", action="store_true",
                        help="also open the plot instead of only writing the JSON")


def embed_command(args):
    # Same projection the web's embedding map serves; here it lands as JSON, so
    # the coordinates can be scripted rather than only looked at.
    matrix = _require(args.input, "Matrix")
    rows, cols, values = matrix_io.plane(matrix, args.feature)
    result = embed(values, axis=args.axis, method=args.method, k=args.k)
    names = cols if args.axis == "domains" else rows

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        {"axis": args.axis, "method": args.method, "k": args.k, "names": names, **result},
        indent=2), encoding="utf-8")

    print(f"{len(names)} {args.axis} projected with {args.method.upper()} into "
          f"{result['n_clusters']} clusters -> {args.output}")
    if result.get("note"):
        print(result["note"])
    if args.show:
        from visualization.display_embedding import display_embedding
        display_embedding(result, names, axis=args.axis, method=args.method)


def display_cor_args(parser):
    _input(parser, CORRELATION_MATRIX_PATH, "correlation matrix to plot")


def display_cor_command(args):
    display_species_domain_heatmap(str(_require(args.input, "Correlation matrix")))


def display_cor_features_args(parser):
    _input(parser, FEATURE_MATRIX_PATH, "feature matrix to plot")


def display_cor_features_command(args):
    display_species_domain_heatmap_with_features(str(_require(args.input, "Feature matrix")))


def display_heatmap_spxsp_args(parser):
    _input(parser, CORRELATION_MATRIX_PATH, "correlation matrix to plot")


def display_heatmap_spxsp_command(args):
    display_heatmap_speciesxspecies(str(_require(args.input, "Correlation matrix")))


Command = namedtuple("Command", "run add_arguments help")

COMMANDS = {
    "--analyze": Command(analyze_command, analyze_args,
                         "Build the correlation and feature matrices from a BLAST file"),
    "--construct_tree": Command(construct_tree_command, construct_tree_args,
                                "Build a phylogenetic tree from a correlation matrix"),
    "--display_tree": Command(display_tree_command, display_tree_args,
                              "Draw a Newick tree (interactive Plotly figure)"),
    "--display_cor": Command(display_cor_command, display_cor_args,
                             "Species x domain heatmap"),
    "--display_cor_features": Command(display_cor_features_command, display_cor_features_args,
                                      "Species x domain heatmap, per feature"),
    "--display_heatmap_spxsp": Command(display_heatmap_spxsp_command, display_heatmap_spxsp_args,
                                       "Species x species heatmap"),
    "--all_vs_all": Command(all_vs_all_command, all_vs_all_args,
                            "Cluster domains (MCL) and open the Dash explorer"),
    "--validate_clusters": Command(validate_clusters_command, validate_clusters_args,
                                   "Print a clustering-quality report (no UI)"),
    "--embed": Command(embed_command, embed_args,
                       "Project profiles into 2D (PCA/t-SNE) and write the coordinates"),
}

# ``--analyze`` is what the docs have always said; ``analyze`` is what a person
# types when they expect a normal CLI. Both resolve to the same command.
ALIASES = {name.lstrip("-"): name for name in COMMANDS}


def usage():
    print("Usage: python main.py [command] [options]")
    print("       python main.py [command] --help     (options for one command)\n")
    width = max(len(name) for name in COMMANDS)
    for name, command in COMMANDS.items():
        print(f"  {name:<{width}}  {command.help}")


def main(argv=None):
    config.setup_logging()
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv:
        usage()
        sys.exit(1)

    requested = argv[0]
    if requested in ("-h", "--help", "help"):
        usage()
        return

    name = requested if requested in COMMANDS else ALIASES.get(requested.lstrip("-"))
    if name is None:
        print(f"Invalid command: {requested}\n")
        usage()
        sys.exit(1)

    command = COMMANDS[name]
    parser = argparse.ArgumentParser(prog=f"python main.py {name}", description=command.help)
    command.add_arguments(parser)
    args = parser.parse_args(argv[1:])

    try:
        command.run(args)
    except Exception as e:
        logging.getLogger(__name__).exception("command %s failed", name)
        print(f"An error occurred while executing '{name}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
