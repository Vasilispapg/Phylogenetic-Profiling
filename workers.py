"""
Entry points for background jobs.

These run in a **separate process** (see ``app.submit``), so they must be
importable at module level and must not import the Flask app. They talk to the
rest of the system only through the SQLite job store, which is why progress
reporting works across the process boundary.

Running them out-of-process matters: Neighbour-Joining is pure Python and holds
the GIL, so as an in-process thread it degraded every concurrent HTTP request.
"""
import logging

import jobs
from analysis.clustering_analysis import cluster_payload
from tree_construction.construct_tree import compute_square_distances, construct_tree

log = logging.getLogger(__name__)


def warm_up():
    """
    Pool initialiser: pay the expensive imports once per worker process.

    ``import markov_clustering`` (which drags in scikit-learn) takes ~0.97 s in a
    cold interpreter. Doing it lazily inside the first job made that latency
    visible to whoever submitted it; doing it here moves the cost to when the
    pool spins up.
    """
    try:
        import markov_clustering  # noqa: F401
        import sklearn.cluster    # noqa: F401
    except Exception:             # noqa: BLE001 - a slow first job beats no pool
        log.warning("worker warm-up failed; imports will happen on first use",
                    exc_info=True)
    jobs.init()


def run_tree_job(job_id, input_path, result_path, display_name, method="nj"):
    """Build a phylogenetic tree from a correlation matrix CSV."""
    jobs.init()
    try:
        jobs.progress(job_id, 0.1, "Reading the correlation matrix...")
        species, distances = compute_square_distances(input_path)
        jobs.progress(job_id, 0.35,
                      f"Building the {method.upper()} tree for {len(species)} species...")
        construct_tree(species, distances, output_path=result_path, method=method)
        jobs.finish(job_id, {"download": result_path.rsplit("/", 1)[-1],
                             "name": display_name, "n_species": len(species)})
    except Exception as exc:                       # noqa: BLE001 - reported to the client
        log.exception("tree job %s failed", job_id)
        jobs.fail(job_id, exc)


def run_allvsall_job(job_id, input_path):
    """Cluster domains by shared phylogenetic profile (MCL)."""
    jobs.init()
    try:
        payload = cluster_payload(
            input_path,
            progress=lambda fraction, message: jobs.progress(job_id, fraction, message),
        )
        # Stored in the shape the endpoint returns, so the default response can
        # stream the compressed blob straight through without re-serialising.
        jobs.finish(job_id, {"blob": jobs.store_blob({"status": "success", **payload})})
    except Exception as exc:                       # noqa: BLE001 - reported to the client
        log.exception("all-vs-all job %s failed", job_id)
        jobs.fail(job_id, exc)
