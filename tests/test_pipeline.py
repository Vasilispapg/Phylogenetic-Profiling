import textwrap

import pytest

from analysis.utils import extract_species, extract_partial_species
from analysis.matrix_operations import (
    create_correlation_matrix,
    create_feature_matrix,
    find_true_positives,
)
from tree_construction.construct_tree import compute_distance_matrix, construct_tree


# Three species (S1, S2, S3), two domains (D1, D2).
#   D1 hits: S1, S2, S3        D2 hits: S1, S2
SAMPLE_BLAST = textwrap.dedent("""\
D1\tUP000000001-00000001-Aaa_aaaa-22-000001-E-000001\t90.0\t100\t1\t0\t1\t100\t1\t100\t0.0\t300
D1\tUP000000002-00000002-Bbb_bbbb-22-000002-E-000002\t88.0\t100\t2\t0\t1\t100\t1\t100\t0.0\t290
D1\tUP000000003-00000003-Ccc_cccc-22-000003-E-000003\t87.0\t100\t3\t0\t1\t100\t1\t100\t0.0\t280
D2\tUP000000001-00000001-Aaa_aaaa-22-000001-E-000009\t70.0\t50\t4\t0\t1\t50\t1\t50\t1e-30\t120
D2\tUP000000002-00000002-Bbb_bbbb-22-000002-E-000009\t72.0\t50\t5\t0\t1\t50\t1\t50\t1e-30\t125
""")

S1 = "UP000000001-00000001-Aaa_aaaa-22"
S2 = "UP000000002-00000002-Bbb_bbbb-22"
S3 = "UP000000003-00000003-Ccc_cccc-22"


@pytest.fixture
def blast_file(tmp_path):
    p = tmp_path / "sample.blastp"
    p.write_text(SAMPLE_BLAST)
    return str(p)


# --------------------------------------------------------------------------- #
# extract_species
# --------------------------------------------------------------------------- #
def test_extract_species_basic():
    assert extract_species("UP000005640-00009606-Homo_sapi-22-001536-E-013170") == \
        "UP000005640-00009606-Homo_sapi-22"


@pytest.mark.parametrize("value, expected", [
    ("a-b", "a-b"),          # fewer than 4 segments -> returned unchanged
    ("", ""),                # empty
    (None, None),            # non-string
    (123, 123),              # non-string
])
def test_extract_species_edge_cases(value, expected):
    assert extract_species(value) == expected


def test_extract_partial_species_fallback():
    assert extract_partial_species("no-match") == "no-match"
    assert extract_partial_species(None) is None


# --------------------------------------------------------------------------- #
# matrix builders
# --------------------------------------------------------------------------- #
def test_correlation_and_feature_share_species_labels(blast_file, tmp_path):
    corr = create_correlation_matrix(blast_file, output_path=str(tmp_path / "c.csv"))
    feat = create_feature_matrix(blast_file, output_path=str(tmp_path / "f.csv"))

    assert set(map(str, corr.index)) == {S1, S2, S3}
    # Same species key in both matrices (the C5 fix).
    assert set(map(str, corr.index)) == set(map(str, feat["Species"]))


def test_correlation_counts(blast_file, tmp_path):
    corr = create_correlation_matrix(blast_file, output_path=str(tmp_path / "c.csv"))
    assert corr.loc[S1, "D1"] == 1
    assert corr.loc[S1, "D2"] == 1
    assert corr.loc[S3, "D2"] == 0  # S3 has no D2 hit


def test_find_true_positives(blast_file, tmp_path):
    out = str(tmp_path / "c.csv")
    create_correlation_matrix(blast_file, output_path=out)
    tp = set(find_true_positives(out))
    assert (S1, "D1") in tp
    assert (S3, "D1") in tp
    assert (S3, "D2") not in tp
    assert len(tp) == 5


def test_find_true_positives_empty(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("Species\n")  # header only, no data
    assert find_true_positives(str(p)) == []


# --------------------------------------------------------------------------- #
# distance matrix / tree
# --------------------------------------------------------------------------- #
def test_compute_distance_matrix_jaccard(blast_file, tmp_path):
    out = str(tmp_path / "c.csv")
    create_correlation_matrix(blast_file, output_path=out)
    species, lt = compute_distance_matrix(out)

    assert set(species) == {S1, S2, S3}
    # lower-triangular shape + zero diagonal
    assert all(len(lt[i]) == i + 1 for i in range(len(lt)))
    assert all(lt[i][i] == 0 for i in range(len(lt)))
    # S1 and S2 have identical profiles -> distance 0
    idx = {s: i for i, s in enumerate(species)}
    i, j = sorted((idx[S1], idx[S2]))
    assert lt[j][i] == pytest.approx(0.0)


def test_compute_distance_matrix_drops_empty_and_requires_two(tmp_path):
    # One real species and one all-zero species -> after dropping, only 1 left.
    p = tmp_path / "c.csv"
    p.write_text("Species,D1,D2\n" + f"{S1},1,0\n" + f"{S2},0,0\n")
    with pytest.raises(ValueError):
        compute_distance_matrix(str(p))


def test_construct_tree_builds_newick(blast_file, tmp_path):
    out = str(tmp_path / "c.csv")
    create_correlation_matrix(blast_file, output_path=out)
    species, lt = compute_distance_matrix(out)
    nw = tmp_path / "tree.nw"
    construct_tree(species, lt, output_path=str(nw))

    from Bio import Phylo
    tree = Phylo.read(str(nw), "newick")
    assert tree.count_terminals() == 3


def test_construct_tree_rejects_single_species(tmp_path):
    with pytest.raises(ValueError):
        construct_tree(["only-one"], [[0.0]], output_path=str(tmp_path / "x.nw"))


# --------------------------------------------------------------------------- #
# domain-profile clustering + validation
# --------------------------------------------------------------------------- #
def test_cluster_domains_finds_two_modules(tmp_path):
    # Two clearly separated modules: P1-* present in s1..s3, P2-* in s4..s6.
    csv = (
        "Species,P1-a,P1-b,P2-a,P2-b\n"
        "s1,1,1,0,0\n"
        "s2,1,1,0,0\n"
        "s3,1,1,0,0\n"
        "s4,0,0,1,1\n"
        "s5,0,0,1,1\n"
        "s6,0,0,1,1\n"
    )
    from analysis.clustering_analysis import (
        cluster_domains, domain_jaccard, build_domain_graph, validate_clusters,
    )
    import networkx as nx
    import markov_clustering as mc
    from scipy.sparse import csr_matrix

    p = tmp_path / "corr.csv"
    p.write_text(csv)

    graph, nodes, allvsall, pos, metrics = cluster_domains(str(p), threshold=0.5, inflation=2.0)
    assert set(nodes) == {"P1-a", "P1-b", "P2-a", "P2-b"}
    # P1-a and P1-b co-cluster; P1-a and P2-a do not.
    assert allvsall.loc["P1-a", "P1-b"] == 1
    assert allvsall.loc["P1-a", "P2-a"] == 0

    # Validation report on the same partition.
    domains, J = domain_jaccard(__import__("pandas").read_csv(str(p), index_col=0))
    g = build_domain_graph(domains, J, 0.5)
    adj = csr_matrix(nx.to_scipy_sparse_array(g, nodelist=domains, weight="weight"))
    clusters = mc.get_clusters(mc.run_mcl(adj, inflation=2.0))
    report = validate_clusters(g, clusters, domains)
    assert report["n_clusters"] == 2
    assert report["same_protein_cocluster_rate"] == 1.0
    assert report["modularity"] > 0.3          # clear structure
    assert report["warning"] is None
