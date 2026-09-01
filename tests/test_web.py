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
BLAST_TSV = (
    b"D1\tUP000000001-00000001-Aaa_aaaa-22-1-E-1\t90.0\t100\t1\t0\t1\t100\t1\t100\t0.0\t300\n"
    b"D1\tUP000000002-00000002-Bbb_bbbb-22-2-E-2\t88.0\t100\t2\t0\t1\t100\t1\t100\t0.0\t290\n"
    b"D2\tUP000000001-00000001-Aaa_aaaa-22-1-E-9\t70.0\t50\t4\t0\t1\t50\t1\t50\t1e-30\t120\n"
)


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
# SPA
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", ["/", "/blast", "/heatmap", "/clustergram-page",
                                  "/tree-builder", "/how-to", "/faq", "/deep/link"])
def test_spa_serves_every_client_route(client, path):
    """Any non-API path returns the bundle so client-side routing works."""
    resp = client.get(path)
    if resp.status_code == 503:
        pytest.skip("frontend/dist is not built")
    assert resp.status_code == 200
    assert b"<div id=\"root\"></div>" in resp.data


def test_spa_does_not_shadow_the_api(client):
    """Unknown /api paths must 404, not fall through to index.html."""
    assert client.get("/api/downloads/nope-not-here.csv").status_code == 404
    assert client.get("/api/nonexistent").status_code == 404


def test_api_and_spa_route_names_can_coincide(client):
    """/clustergram and /embedding are React routes AND used to be endpoints."""
    for path in ("/clustergram", "/embedding", "/explorer"):
        resp = client.get(path)
        if resp.status_code == 503:
            pytest.skip("frontend/dist is not built")
        assert resp.status_code == 200
        assert b"<div id=\"root\"></div>" in resp.data


def test_health(client):
    body = client.get("/api/health").get_json()
    assert body["status"] == "success"
    assert "spa_built" in body


# --------------------------------------------------------------------------- #
# Downloads
# --------------------------------------------------------------------------- #
def test_download_path_traversal_blocked(client):
    resp = client.get("/api/downloads/..%2f..%2fapp.py")
    assert resp.status_code in (403, 404)


# --------------------------------------------------------------------------- #
# Upload / process
# --------------------------------------------------------------------------- #
def test_upload_rejects_bad_extension(client):
    resp = upload(client, "/api/upload", b"junk", "evil.exe")
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "error"


def test_tree_construct_also_rejects_bad_extension(client):
    """This endpoint used to skip the allowlist entirely."""
    assert upload(client, "/api/trees", b"junk", "evil.exe").status_code == 400


def test_allvsall_rejects_bad_extension(client):
    assert upload(client, "/api/allvsall", b"junk", "evil.exe").status_code == 400


def test_upload_then_process_roundtrip(client):
    up = upload(client, "/api/upload", BLAST_TSV, "hits.blastp").get_json()
    assert up["status"] == "success"

    done = client.post("/api/process", json={"filename": up["filename"],
                                         "analysis_type": "correlation"}).get_json()
    assert done["status"] == "success"
    assert client.get(f"/api/downloads/{done['filename']}").status_code == 200
    assert client.get(f"/api/results?filename={done['filename']}").status_code == 200


def test_two_uploads_with_the_same_name_do_not_collide(client):
    """The bug this replaced: both users wrote to uploads/<name> and to a fixed
    downloads/correlation_matrix.csv, so one silently served the other's data."""
    a = upload(client, "/api/upload", BLAST_TSV, "shared.txt").get_json()
    b = upload(client, "/api/upload", BLAST_TSV, "shared.txt").get_json()
    assert a["filename"] != b["filename"]
    assert a["original_name"] == b["original_name"] == "shared.txt"


def test_process_missing_file(client):
    resp = client.post("/api/process", json={"filename": "x.csv", "analysis_type": "correlation"})
    assert resp.status_code == 404
    assert resp.get_json()["status"] == "error"


def test_process_rejects_unknown_analysis_type(client):
    assert client.post("/api/process", json={"filename": "x.csv",
                                         "analysis_type": "wishful"}).status_code == 400


# --------------------------------------------------------------------------- #
# Clustergram / embedding
# --------------------------------------------------------------------------- #
def test_clustergram_orders_both_axes(client):
    body = client.post("/api/clustergram", json={"z": SMALL_Z}).get_json()
    assert body["status"] == "success"
    assert sorted(body["row_order"]) == [0, 1, 2, 3]
    assert sorted(body["col_order"]) == [0, 1, 2, 3]
    assert len(body["row_dendro"]["icoord"]) == len(body["row_dendro"]["dcoord"])


def test_clustergram_rejects_empty(client):
    assert client.post("/api/clustergram", json={}).status_code == 400


def test_clustergram_rejects_non_numeric(client):
    assert client.post("/api/clustergram", json={"z": [["a", "b"], ["c", "d"]]}).status_code == 400


def test_embedding_shapes(client):
    body = client.post("/api/embedding", json={"z": SMALL_Z, "axis": "domains",
                                           "method": "pca", "k": 2}).get_json()
    assert len(body["coords"]) == 4
    assert all(len(c) == 2 for c in body["coords"])
    assert len(body["labels"]) == 4


def test_embedding_rejects_unknown_method(client):
    assert client.post("/api/embedding", json={"z": SMALL_Z, "method": "magic"}).status_code == 400


def test_embedding_needs_enough_points(client):
    assert client.post("/api/embedding", json={"z": [[1, 0], [0, 1]],
                                           "axis": "species"}).status_code == 400


# --------------------------------------------------------------------------- #
# Async jobs
# --------------------------------------------------------------------------- #
def test_tree_status_requires_job_id(client):
    """Without an id the route does not exist -- the SPA fallback must not answer."""
    assert client.get("/api/trees/").status_code == 404


def test_tree_status_unknown_job(client):
    assert client.get("/api/trees/does-not-exist").status_code == 404


def test_tree_construct_job_completes_and_downloads(client):
    started = upload(client, "/api/trees", MATRIX_CSV, "corr.csv")
    assert started.status_code == 202
    job_id = started.get_json()["job_id"]

    final = wait_for(
        lambda: client.get(f"/api/trees/{job_id}").get_json(),
        lambda d: d["status"] in ("completed", "failed"),
    )
    assert final["status"] == "completed", final
    assert client.get(final["download_url"]).status_code == 200
    assert final["original_filename"] == "corr.nw"


def test_tree_construct_rejects_unknown_method(client):
    assert upload(client, "/api/trees", MATRIX_CSV, "corr.csv",
                  method="wishful").status_code == 400


def test_allvsall_job_completes_with_a_lean_payload(client):
    started = upload(client, "/api/allvsall", MATRIX_CSV, "corr.csv").get_json()
    job_id = started["job_id"]

    wait_for(lambda: client.get(f"/api/allvsall/{job_id}/status").get_json(),
             lambda d: d["state"] in ("done", "failed"))

    body = client.get(f"/api/allvsall/{job_id}/data").get_json()
    assert body["status"] == "success"
    assert body["metrics"]["n_clusters"] == 2
    assert body["node_cluster"]["P1-a"] == body["node_cluster"]["P1-b"]
    assert body["node_cluster"]["P1-a"] != body["node_cluster"]["P2-a"]
    # The O(n^2) co-cluster matrix is never stored or sent by default.
    assert "matrix" not in body and "positions" not in body
    assert body["edges_total"] >= len(body["edges"])


def test_allvsall_matrix_is_derived_on_request(client):
    started = upload(client, "/api/allvsall", MATRIX_CSV, "corr.csv").get_json()
    job_id = started["job_id"]
    wait_for(lambda: client.get(f"/api/allvsall/{job_id}/status").get_json(),
             lambda d: d["state"] in ("done", "failed"))

    body = client.get(f"/api/allvsall/{job_id}/data?include=matrix").get_json()
    nodes, matrix = body["nodes"], body["matrix"]
    assert len(matrix) == len(nodes)
    clusters = body["node_cluster"]
    for i, a in enumerate(nodes):
        for j, b in enumerate(nodes):
            assert matrix[i][j] == int(clusters[a] == clusters[b])


def test_allvsall_data_is_served_gzipped(client):
    """The blob is stored compressed and streamed without a round trip."""
    started = upload(client, "/api/allvsall", MATRIX_CSV, "corr.csv").get_json()
    job_id = started["job_id"]
    wait_for(lambda: client.get(f"/api/allvsall/{job_id}/status").get_json(),
             lambda d: d["state"] in ("done", "failed"))

    resp = client.get(f"/api/allvsall/{job_id}/data", headers={"Accept-Encoding": "gzip"})
    assert resp.headers.get("Content-Encoding") == "gzip"

    plain = client.get(f"/api/allvsall/{job_id}/data", headers={"Accept-Encoding": "identity"})
    assert plain.headers.get("Content-Encoding") is None
    assert plain.get_json()["status"] == "success"


def test_allvsall_status_unknown_job(client):
    assert client.get("/api/allvsall/nope/status").status_code == 404


def test_allvsall_data_before_completion(client):
    """A job that exists but is not finished is a 409, not a fake success."""
    import jobs
    job_id = jobs.create("allvsall", "queued")
    assert client.get(f"/api/allvsall/{job_id}/data").status_code == 409


def test_allvsall_data_for_a_failed_job(client):
    import jobs
    job_id = jobs.create("allvsall")
    jobs.fail(job_id, "boom")
    assert client.get(f"/api/allvsall/{job_id}/data").status_code == 422


# --------------------------------------------------------------------------- #
# Tree viewer
# --------------------------------------------------------------------------- #
def test_tree_viewer_parses_newick(client):
    body = upload(client, "/api/newick", b"(A:0.1,(B:0.2,C:0.2):0.1);", "t.nw").get_json()
    assert body["status"] == "success"
    assert body["max_depth_tree"] == 2
    assert {c["name"] for c in body["tree_data"]["children"]} >= {"A"}


def test_tree_viewer_rejects_garbage(client):
    assert upload(client, "/api/newick", b"not a tree at all", "t.nw").status_code == 400


# --------------------------------------------------------------------------- #
# Matrix by id
#
# The clustergram and embedding endpoints used to require the whole matrix in
# the request body. Uploading once and referencing it by id is the path the SPA
# now takes; the `z` form is kept for small ad-hoc matrices.
# --------------------------------------------------------------------------- #
FEATURE_CSV = (
    b'Species,D1,D2\n'
    b's1,"{""num_hits"": 3, ""mean_bitscore"": 300}","{""num_hits"": 0, ""mean_bitscore"": 0}"\n'
    b's2,"{""num_hits"": 1, ""mean_bitscore"": 120}","{""num_hits"": 2, ""mean_bitscore"": 240}"\n'
    b's3,"{""num_hits"": 0, ""mean_bitscore"": 0}","{""num_hits"": 5, ""mean_bitscore"": 480}"\n'
)


def test_matrix_upload_returns_metadata_not_values(client):
    body = upload(client, "/api/matrices", MATRIX_CSV, "corr.csv").get_json()
    assert body["status"] == "success"
    assert body["kind"] == "numeric"
    assert body["rows"] == ["s1", "s2", "s3", "s4", "s5", "s6"]
    assert body["cols"] == ["P1-a", "P1-b", "P2-a", "P2-b"]
    assert body["features"] == ["value"]
    # The response is O(rows + cols): no cell values travel back.
    assert "z" not in body and "values" not in body


def test_matrix_upload_detects_a_feature_matrix(client):
    body = upload(client, "/api/matrices", FEATURE_CSV, "feat.csv").get_json()
    assert body["kind"] == "feature"
    assert set(body["features"]) == {"num_hits", "mean_bitscore"}


def test_matrix_upload_rejects_garbage(client):
    assert upload(client, "/api/matrices", b"", "empty.csv").status_code == 400


def test_clustergram_by_file_id(client):
    file_id = upload(client, "/api/matrices", MATRIX_CSV, "corr.csv").get_json()["file_id"]
    body = client.post("/api/clustergram", json={"file_id": file_id}).get_json()
    assert body["status"] == "success"
    assert sorted(body["row_order"]) == [0, 1, 2, 3, 4, 5]
    assert sorted(body["col_order"]) == [0, 1, 2, 3]


def test_clustergram_by_file_id_selects_the_metric(client):
    file_id = upload(client, "/api/matrices", FEATURE_CSV, "feat.csv").get_json()["file_id"]
    for metric in ("num_hits", "mean_bitscore"):
        body = client.post("/api/clustergram", json={"file_id": file_id,
                                                 "metric": metric}).get_json()
        assert body["status"] == "success", metric


def test_embedding_by_file_id(client):
    file_id = upload(client, "/api/matrices", MATRIX_CSV, "corr.csv").get_json()["file_id"]
    body = client.post("/api/embedding", json={"file_id": file_id, "axis": "domains",
                                           "method": "pca", "k": 2}).get_json()
    assert len(body["coords"]) == 4          # four domains
    assert len(body["labels"]) == 4


def test_unknown_file_id(client):
    assert client.post("/api/clustergram", json={"file_id": "nope"}).status_code == 404
    assert client.post("/api/embedding", json={"file_id": "nope"}).status_code == 404


def test_file_id_cannot_escape_the_upload_directory(client):
    resp = client.post("/api/clustergram", json={"file_id": "../../app.py"})
    assert resp.status_code == 404


def test_missing_asset_404s_instead_of_returning_html(client):
    """A broken asset reference must not come back as index.html with a 200."""
    assert client.get("/assets/does-not-exist.js").status_code in (404, 503)
    assert client.get("/favicon.ico").status_code in (404, 503)


# --------------------------------------------------------------------------- #
# t-SNE at small point counts
#
# scikit-learn requires perplexity < n_samples, and the old formula had a floor
# of 5, so every projection of five points or fewer failed — the exact size of a
# small domain set. The client showed an empty panel because the error was
# rendered only while the request was still in flight.
# --------------------------------------------------------------------------- #
def _matrix_csv(rows, cols):
    header = "Species," + ",".join(f"D{j}" for j in range(cols))
    body = "".join(f"s{i}," + ",".join(str((i * 3 + j) % 5) for j in range(cols)) + "\n"
                   for i in range(rows))
    return (header + "\n" + body).encode()


# t-SNE is slow, so this covers the sizes that matter rather than a grid: the
# smallest allowed, the size that was reported broken, and a normal one.
@pytest.mark.parametrize("rows, cols, axis, expected", [
    (3, 3, "species", 3),      # MIN_POINTS, the boundary
    (8, 5, "domains", 5),      # the reported failure
    (14, 6, "species", 14),    # a size where t-SNE is actually meaningful
])
def test_tsne_works_at_every_allowed_size(client, rows, cols, axis, expected):
    file_id = upload(client, "/api/matrices", _matrix_csv(rows, cols), "m.csv").get_json()["file_id"]
    resp = client.post("/api/embedding",
                       json={"file_id": file_id, "axis": axis, "method": "tsne", "k": 3})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert len(body["coords"]) == expected
    assert all(len(point) == 2 for point in body["coords"])


def test_tsne_says_when_there_are_too_few_points_to_mean_anything(client):
    file_id = upload(client, "/api/matrices", _matrix_csv(5, 5), "m.csv").get_json()["file_id"]
    small = client.post("/api/embedding", json={"file_id": file_id, "axis": "domains",
                                                "method": "tsne"}).get_json()
    assert "note" in small and "PCA" in small["note"]


def test_tsne_is_quiet_when_there_are_enough_points(client):
    file_id = upload(client, "/api/matrices", _matrix_csv(14, 6), "m.csv").get_json()["file_id"]
    big = client.post("/api/embedding", json={"file_id": file_id, "axis": "species",
                                              "method": "tsne"}).get_json()
    assert "note" not in big


def test_pca_is_unaffected_at_small_sizes(client):
    file_id = upload(client, "/api/matrices", _matrix_csv(3, 3), "m.csv").get_json()["file_id"]
    resp = client.post("/api/embedding", json={"file_id": file_id, "axis": "domains",
                                               "method": "pca"})
    assert resp.status_code == 200
    assert "note" not in resp.get_json()
