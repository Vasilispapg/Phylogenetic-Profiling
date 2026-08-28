"""
Domain-profile clustering (phylogenetic profiling).

Phylogenetic profiling groups domains that share the same presence/absence
pattern across species. We therefore cluster a DOMAIN x DOMAIN similarity graph
(not the raw bipartite species-domain graph): an edge connects two domains whose
binary profiles are similar (Jaccard >= threshold), and MCL finds the modules.
``validate_clusters`` reports whether the result is meaningful.

This module is deliberately free of any UI framework so that importing a web
blueprint does not drag Dash/Plotly in. The Dash explorer now lives in
``visualization/dash_allvsall.py`` and is only reachable from the CLI.
"""
import gzip
import hashlib
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import modularity
from scipy.sparse import csr_matrix

from config import CACHE_DIR, EDGE_BUDGET_PER_NODE, JACCARD_THRESHOLD, MCL_INFLATION

log = logging.getLogger(__name__)

# Kept as module-level names because main.py and the tests import them.
DEFAULT_THRESHOLD = JACCARD_THRESHOLD   # minimum Jaccard similarity for an edge
DEFAULT_INFLATION = MCL_INFLATION       # MCL granularity

# Bump when the payload shape or the algorithm changes, to invalidate the cache.
CACHE_VERSION = 1


def _noop(fraction, message):
    """Default progress sink."""


def domain_jaccard(corr_df):
    """Return (domains, JxJ Jaccard-similarity matrix) from a species x domain
    correlation matrix (presence == value > 0)."""
    b = (corr_df.to_numpy() > 0).astype(float)         # species x domains
    domains = [str(c) for c in corr_df.columns]
    inter = b.T @ b                                    # shared species per domain pair
    pres = b.sum(axis=0)
    union = pres[:, None] + pres[None, :] - inter
    with np.errstate(divide="ignore", invalid="ignore"):
        j = np.where(union > 0, inter / union, 0.0)
    np.fill_diagonal(j, 0.0)
    return domains, j


def build_domain_graph(domains, j, threshold):
    """Weighted domain graph: edge (a, b) with weight J[a,b] when J >= threshold."""
    graph = nx.Graph()
    graph.add_nodes_from(domains)
    iu, ju = np.triu_indices(len(domains), k=1)
    mask = j[iu, ju] >= threshold
    iu, ju = iu[mask], ju[mask]
    graph.add_weighted_edges_from(
        (domains[a], domains[b], float(j[a, b])) for a, b in zip(iu, ju)
    )
    return graph


def cluster_labels(clusters, n_domains):
    """Cluster index per domain, as a numpy array. The MCL output already knows
    this; deriving it here means no caller has to re-discover it with
    connected_components on a dense co-cluster matrix."""
    labels = np.full(n_domains, -1, dtype=np.int32)
    for cluster_index, members in enumerate(clusters):
        labels[list(members)] = cluster_index
    return labels


def co_cluster_matrix(labels):
    """Dense domain x domain co-cluster matrix, vectorised."""
    return (labels[:, None] == labels[None, :]).astype(np.uint8)


def validate_clusters(graph, clusters, nodes):
    """
    Quality report for an MCL partition. MCL is unsupervised (there is no
    training), so we report:
      - cluster count / sizes,
      - modularity Q of the partition on the similarity graph,
      - same-protein co-clustering rate: an internal ground truth -- domains of
        the same protein accession (prefix before the first '-') are physically
        linked and should land in the same cluster,
      - a warning when the partition collapses to one big group (no structure).
    """
    sizes = sorted((len(c) for c in clusters), reverse=True)
    label = {}
    for ci, c in enumerate(clusters):
        for i in c:
            label[nodes[i]] = ci

    partition = [set(nodes[i] for i in c) for c in clusters]
    try:
        q = float(modularity(graph, partition, weight="weight"))
    except Exception:
        q = float("nan")

    groups = defaultdict(list)
    for node in nodes:
        groups[str(node).split("-")[0]].append(node)
    same_pairs = [
        (a, b)
        for members in groups.values() if len(members) > 1
        for x, a in enumerate(members) for b in members[x + 1:]
    ]
    if same_pairs:
        same_rate = float(np.mean([
            1.0 if label.get(a) == label.get(b) else 0.0 for a, b in same_pairs
        ]))
    else:
        same_rate = float("nan")

    largest = sizes[0] if sizes else 0
    warning = None
    if nodes and (largest >= 0.8 * len(nodes) or (q == q and q < 0.05)):
        warning = (
            "Little/no community structure (modularity ~0; one dominant cluster). "
            "The domain profiles are too uniform to form meaningful modules. "
            "Consider a stricter presence threshold (e-value/bitscore cutoff) when "
            "building the correlation matrix, a higher Jaccard threshold, or richer data."
        )

    return {
        "n_domains": len(nodes),
        "n_clusters": len(clusters),
        "n_nontrivial_clusters": sum(1 for s in sizes if s > 1),
        "largest_cluster": largest,
        "cluster_sizes_top": sizes[:10],
        "modularity": round(q, 4) if q == q else None,
        "same_protein_cocluster_rate": round(same_rate, 4) if same_rate == same_rate else None,
        "warning": warning,
    }


def _run_mcl(graph, domains, inflation):
    # Imported lazily: markov_clustering pulls in scikit-learn (measured 441 ms of
    # the app's import time), and the web process should not pay that at boot.
    import markov_clustering as mc

    started = time.time()
    adj = csr_matrix(nx.to_scipy_sparse_array(graph, nodelist=domains, weight="weight"))
    clusters = mc.get_clusters(mc.run_mcl(adj, inflation=inflation))
    log.info("MCL on %d domains: %d clusters in %.2fs",
             len(domains), len(clusters), time.time() - started)
    return clusters


def _core(corr_matrix_path, threshold, inflation, progress=_noop):
    """Shared pipeline: correlation matrix -> (domains, graph, clusters, labels, metrics)."""
    progress(0.05, "Reading correlation matrix...")
    corr_df = pd.read_csv(corr_matrix_path, index_col=0)

    progress(0.20, f"Computing Jaccard similarity for {corr_df.shape[1]} domains...")
    domains, j = domain_jaccard(corr_df)

    progress(0.40, "Building the domain similarity graph...")
    graph = build_domain_graph(domains, j, threshold)

    progress(0.55, f"Running Markov clustering ({graph.number_of_edges():,} edges)...")
    clusters = _run_mcl(graph, domains, inflation)
    labels = cluster_labels(clusters, len(domains))

    progress(0.85, "Validating cluster quality...")
    metrics = validate_clusters(graph, clusters, domains)
    if metrics["warning"]:
        log.warning("cluster validation: %s", metrics["warning"])
    else:
        log.info("cluster validation: %s", metrics)
    return domains, graph, clusters, labels, metrics


def cluster_domains(corr_matrix_path, cache_dir=None, threshold=DEFAULT_THRESHOLD,
                    inflation=DEFAULT_INFLATION, run_dash=False):
    """
    Cluster domains by shared phylogenetic profile.

    Returns ``(graph, nodes, all_vs_all_df, pos, metrics)``. This form builds the
    dense co-cluster matrix and a spring layout, which are O(n^2); the web API
    uses :func:`cluster_payload` instead, which skips both.
    """
    domains, graph, clusters, labels, metrics = _core(corr_matrix_path, threshold, inflation)
    all_vs_all_df = pd.DataFrame(co_cluster_matrix(labels), index=domains, columns=domains)
    pos = nx.spring_layout(graph, seed=0)

    if run_dash:
        from visualization.dash_allvsall import create_dash_app
        create_dash_app(graph, list(graph.nodes()), all_vs_all_df, pos).run(port=8051)
        return None

    return graph, list(graph.nodes()), all_vs_all_df, pos, metrics


def cache_key(path, **params):
    """Content-addressed key: file bytes + parameters + algorithm version."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    digest.update(json.dumps(params, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def cluster_payload(corr_matrix_path, threshold=DEFAULT_THRESHOLD,
                    inflation=DEFAULT_INFLATION, edge_budget_per_node=EDGE_BUDGET_PER_NODE,
                    progress=_noop, cache_dir=None):
    """
    The API-shaped clustering result: O(n) instead of O(n^2) on the wire.

    Drops the dense co-cluster matrix (fully derivable from ``node_cluster``) and
    the spring layout (every client runs its own), and returns only the strongest
    ``edge_budget_per_node * n`` edges -- reporting ``edges_total`` so the UI can
    say what it is hiding instead of truncating silently.
    """
    cache_dir = Path(cache_dir or CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = cache_key(corr_matrix_path, threshold=threshold, inflation=inflation,
                    budget=edge_budget_per_node, v=CACHE_VERSION)
    cached = cache_dir / f"allvsall-{key}.json.gz"
    if cached.exists():
        log.info("cluster_payload cache hit: %s", cached.name)
        progress(1.0, "Loaded from cache.")
        return json.loads(gzip.decompress(cached.read_bytes()).decode("utf-8"))

    domains, graph, _clusters, labels, metrics = _core(
        corr_matrix_path, threshold, inflation, progress
    )

    progress(0.95, "Preparing the network...")
    edges = sorted(
        ({"source": u, "target": v, "weight": round(float(d.get("weight", 1.0)), 3)}
         for u, v, d in graph.edges(data=True)),
        key=lambda e: -e["weight"],
    )
    budget = max(1, edge_budget_per_node) * max(1, len(domains))
    positions = nx.spring_layout(graph, seed=0)
    payload = {
        "nodes": domains,
        "node_cluster": {d: int(labels[i]) for i, d in enumerate(domains)},
        "degree": {d: int(graph.degree(d)) for d in domains},
        "edges": edges[:budget],
        "edges_total": len(edges),
        "metrics": metrics,
        # O(n^2) extras: stored on disk, served only on ?include=
        "matrix": co_cluster_matrix(labels).tolist(),
        "positions": {n: [float(x), float(y)] for n, (x, y) in positions.items()},
    }
    cached.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))
    return payload
