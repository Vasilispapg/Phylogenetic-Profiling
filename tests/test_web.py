import io
import time

import pytest

from app import app as flask_app

MATRIX_CSV = (
    b"Species,P1-a,P1-b,P2-a,P2-b\n"
    b"s1,1,1,0,0\ns2,1,1,0,0\ns3,1,1,0,0\n"
    b"s4,0,0,1,1\ns5,0,0,1,1\ns6,0,0,1,1\n"
)
SMALL_Z = [[1, 0, 1, 0], [1, 0, 1, 0], [0, 1, 0, 1], [0, 1, 0, 1]]


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


def upload(client, url, content, name, **fields):
    return client.post(url, data={"file": (io.BytesIO(content), name), **fields},
                       content_type="multipart/form-data")


def wait_for(fn, done, timeout=90):
    """Poll a job endpoint until it reaches a terminal state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = fn()
        if done(payload):
            return payload
        time.sleep(0.1)
    raise AssertionError(f"job did not finish within {timeout}s: {payload}")


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", [
    "/", "/tools", "/tools/blast", "/tools/allvsall", "/tools/heatmap",
    "/tools/tree_construct", "/tools/tree_viewer", "/how-to", "/faq", "/styleguide",
])
def test_tool_pages_render(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert b"<body" in resp.data.lower()


def test_health(client):
    assert client.get("/health").get_json()["status"] == "success"


# --------------------------------------------------------------------------- #
# Downloads
# --------------------------------------------------------------------------- #
def test_download_missing_file_404(client):
    assert client.get("/downloads/nope-not-here.csv").status_code == 404


def test_download_path_traversal_blocked(client):
    resp = client.get("/downloads/..%2f..%2fapp.py")
    assert resp.status_code in (403, 404)


# --------------------------------------------------------------------------- #
# Upload / process
# --------------------------------------------------------------------------- #
def test_upload_rejects_bad_extension(client):
    resp = upload(client, "/upload", b"junk", "evil.exe")
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "error"


def test_tree_construct_also_rejects_bad_extension(client):
    """This endpoint used to skip the allowlist entirely."""
    assert upload(client, "/tools/tree_construct", b"junk", "evil.exe").status_code == 400


def test_allvsall_rejects_bad_extension(client):
    assert upload(client, "/tools/allvsall", b"junk", "evil.exe").status_code == 400


def test_upload_then_process_roundtrip(client):
    blast = (
        b"D1\tUP000000001-00000001-Aaa_aaaa-22-1-E-1\t90.0\t100\t1\t0\t1\t100\t1\t100\t0.0\t300\n"
        b"D1\tUP000000002-00000002-Bbb_bbbb-22-2-E-2\t88.0\t100\t2\t0\t1\t100\t1\t100\t0.0\t290\n"
        b"D2\tUP000000001-00000001-Aaa_aaaa-22-1-E-9\t70.0\t50\t4\t0\t1\t50\t1\t50\t1e-30\t120\n"
    )
    up = upload(client, "/upload", blast, "hits.blastp").get_json()
    assert up["status"] == "success"

    done = client.post("/process", json={"filename": up["filename"],
                                         "analysis_type": "correlation"}).get_json()
    assert done["status"] == "success"
    assert client.get(f"/downloads/{done['filename']}").status_code == 200
    assert client.get(f"/results?filename={done['filename']}").status_code == 200


def test_two_uploads_with_the_same_name_do_not_collide(client):
    """The bug this replaced: both users wrote to uploads/<name> and to a fixed
    downloads/correlation_matrix.csv, so one silently served the other's data."""
    a = upload(client, "/upload", b"first\n", "shared.csv").get_json()
    b = upload(client, "/upload", b"second\n", "shared.csv").get_json()
    assert a["filename"] != b["filename"]
    assert a["original_name"] == b["original_name"] == "shared.csv"


def test_process_missing_file(client):
    resp = client.post("/process", json={"filename": "x.csv", "analysis_type": "correlation"})
    assert resp.status_code == 404
    assert resp.get_json()["status"] == "error"


def test_process_rejects_unknown_analysis_type(client):
    assert client.post("/process", json={"filename": "x.csv",
                                         "analysis_type": "wishful"}).status_code == 400


# --------------------------------------------------------------------------- #
# Clustergram / embedding
# --------------------------------------------------------------------------- #
def test_clustergram_orders_both_axes(client):
    body = client.post("/clustergram", json={"z": SMALL_Z}).get_json()
    assert body["status"] == "success"
    assert sorted(body["row_order"]) == [0, 1, 2, 3]
    assert sorted(body["col_order"]) == [0, 1, 2, 3]
    assert len(body["row_dendro"]["icoord"]) == len(body["row_dendro"]["dcoord"])


def test_clustergram_rejects_empty(client):
    assert client.post("/clustergram", json={}).status_code == 400


def test_clustergram_rejects_non_numeric(client):
    assert client.post("/clustergram", json={"z": [["a", "b"], ["c", "d"]]}).status_code == 400


def test_embedding_shapes(client):
    body = client.post("/embedding", json={"z": SMALL_Z, "axis": "domains",
                                           "method": "pca", "k": 2}).get_json()
    assert len(body["coords"]) == 4
    assert all(len(c) == 2 for c in body["coords"])
    assert len(body["labels"]) == 4


def test_embedding_rejects_unknown_method(client):
    assert client.post("/embedding", json={"z": SMALL_Z, "method": "magic"}).status_code == 400


def test_embedding_needs_enough_points(client):
    assert client.post("/embedding", json={"z": [[1, 0], [0, 1]],
                                           "axis": "species"}).status_code == 400


# --------------------------------------------------------------------------- #
# Async jobs
# --------------------------------------------------------------------------- #
def test_tree_status_requires_job_id(client):
    assert client.get("/tools/tree_status").status_code == 400


def test_tree_status_unknown_job(client):
    assert client.get("/tools/tree_status?job_id=does-not-exist").status_code == 404


def test_tree_construct_job_completes_and_downloads(client):
    started = upload(client, "/tools/tree_construct", MATRIX_CSV, "corr.csv")
    assert started.status_code == 202
    job_id = started.get_json()["job_id"]

    final = wait_for(
        lambda: client.get(f"/tools/tree_status?job_id={job_id}").get_json(),
        lambda d: d["status"] in ("completed", "failed"),
    )
    assert final["status"] == "completed", final
    assert client.get(final["download_url"]).status_code == 200
    assert final["original_filename"] == "corr.nw"


def test_tree_construct_rejects_unknown_method(client):
    assert upload(client, "/tools/tree_construct", MATRIX_CSV, "corr.csv",
                  method="wishful").status_code == 400


def test_allvsall_job_completes_with_a_lean_payload(client):
    started = upload(client, "/tools/allvsall", MATRIX_CSV, "corr.csv").get_json()
    job_id = started["filename"]

    wait_for(lambda: client.get(f"/allvsall_status/{job_id}").get_json(),
             lambda d: d["state"] in ("done", "failed"))

    body = client.get(f"/allvsall_data/{job_id}").get_json()
    assert body["status"] == "success"
    assert body["metrics"]["n_clusters"] == 2
    assert body["node_cluster"]["P1-a"] == body["node_cluster"]["P1-b"]
    assert body["node_cluster"]["P1-a"] != body["node_cluster"]["P2-a"]
    # The O(n^2) fields are not on the wire unless asked for.
    assert "matrix" not in body and "positions" not in body
    assert body["edges_total"] >= len(body["edges"])

    extra = client.get(f"/allvsall_data/{job_id}?include=matrix,positions").get_json()
    assert len(extra["matrix"]) == len(extra["nodes"])
    assert set(extra["positions"]) == set(extra["nodes"])


def test_allvsall_status_unknown_job(client):
    assert client.get("/allvsall_status/nope").status_code == 404


def test_allvsall_data_before_completion(client):
    """A job that exists but is not finished is a 409, not a fake success."""
    import jobs
    job_id = jobs.create("allvsall", "queued")
    assert client.get(f"/allvsall_data/{job_id}").status_code == 409


def test_allvsall_data_for_a_failed_job(client):
    import jobs
    job_id = jobs.create("allvsall")
    jobs.fail(job_id, "boom")
    assert client.get(f"/allvsall_data/{job_id}").status_code == 422


# --------------------------------------------------------------------------- #
# Tree viewer
# --------------------------------------------------------------------------- #
def test_tree_viewer_parses_newick(client):
    body = upload(client, "/tools/tree_viewer", b"(A:0.1,(B:0.2,C:0.2):0.1);", "t.nw").get_json()
    assert body["status"] == "success"
    assert body["max_depth_tree"] == 2
    assert {c["name"] for c in body["tree_data"]["children"]} >= {"A"}


def test_tree_viewer_rejects_garbage(client):
    assert upload(client, "/tools/tree_viewer", b"not a tree at all", "t.nw").status_code == 400
