"""
The fast tree builder must stay *equivalent* to the reference implementation.

tree_construction/nj.py replaced Bio.Phylo's Neighbour-Joining for speed
(119.9s -> 0.76s on this repo's 848-species matrix). That is only acceptable if
it produces the same tree, so the equivalence is asserted here rather than
assumed.
"""
import io

import numpy as np
import pytest
from Bio import Phylo
from Bio.Phylo.TreeConstruction import DistanceMatrix, DistanceTreeConstructor
from scipy.spatial.distance import pdist, squareform

from tree_construction.nj import build_newick, check_size, nj_newick, upgma_newick


def _splits(tree, names):
    """The set of bipartitions a tree induces: its topology, order-independent."""
    all_names = frozenset(names)
    out = set()
    for clade in tree.get_nonterminals():
        leaves = frozenset(t.name for t in clade.get_terminals())
        if 1 < len(leaves) < len(all_names) - 1:
            out.add(frozenset([leaves, all_names - leaves]))
    return out


def _random_distances(n, d=60, seed=7):
    profiles = np.random.default_rng(seed).random((n, d)) < 0.35
    return squareform(pdist(profiles, metric="jaccard"))


@pytest.mark.parametrize("n", [8, 25, 40])
def test_nj_topology_matches_biopython(n):
    """Robinson-Foulds distance 0 against Bio.Phylo, on several sizes."""
    distances = _random_distances(n)
    names = [f"s{i}" for i in range(n)]
    lower = [[float(distances[i][j]) for j in range(i + 1)] for i in range(n)]

    reference = DistanceTreeConstructor().nj(DistanceMatrix(names=list(names), matrix=lower))
    ours = Phylo.read(io.StringIO(nj_newick(distances, names)), "newick")

    assert _splits(ours, names) == _splits(reference, names)


def test_nj_two_taxa():
    tree = Phylo.read(io.StringIO(nj_newick(np.array([[0.0, 0.4], [0.4, 0.0]]), ["a", "b"])),
                      "newick")
    assert tree.count_terminals() == 2


def test_nj_rejects_single_taxon():
    with pytest.raises(ValueError):
        nj_newick(np.zeros((1, 1)), ["only-one"])


def test_upgma_is_a_valid_tree():
    n = 20
    tree = Phylo.read(io.StringIO(upgma_newick(_random_distances(n), [f"s{i}" for i in range(n)])),
                      "newick")
    assert tree.count_terminals() == n


def test_newick_special_characters_are_quoted():
    """Labels containing Newick punctuation must not corrupt the file."""
    names = ["a b", "c(d)", "e,f"]
    distances = np.array([[0, .4, .6], [.4, 0, .5], [.6, .5, 0]], dtype=float)
    tree = Phylo.read(io.StringIO(nj_newick(distances, names)), "newick")
    assert {t.name for t in tree.get_terminals()} == set(names)


def test_max_taxa_guard_is_actionable(monkeypatch):
    monkeypatch.setattr("tree_construction.nj.MAX_TAXA", 10)
    with pytest.raises(ValueError, match="MAX_TAXA"):
        check_size(11, "nj")
    check_size(11, "upgma")   # the O(n^2) method is not capped by MAX_TAXA


def test_build_newick_rejects_unknown_method():
    with pytest.raises(ValueError, match="Unknown method"):
        build_newick(_random_distances(5), [f"s{i}" for i in range(5)], "wishful")
