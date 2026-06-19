import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


@pytest.mark.parametrize("path", [
    "/",
    "/tools",
    "/tools/blast",
    "/tools/allvsall",
    "/tools/heatmap",
    "/tools/tree_construct",
    "/tools/tree_viewer",
])
def test_tool_pages_render(client, path):
    resp = client.get(path)
    assert resp.status_code == 200


def test_tree_status_requires_job_id(client):
    assert client.get("/tools/tree_status").status_code == 400


def test_tree_status_unknown_job(client):
    resp = client.get("/tools/tree_status?job_id=does-not-exist")
    assert resp.status_code == 404


def test_download_missing_file_404(client):
    assert client.get("/downloads/nope-not-here.csv").status_code == 404


def test_download_path_traversal_blocked(client):
    # send_from_directory must not allow escaping the downloads dir.
    resp = client.get("/downloads/..%2f..%2fapp.py")
    assert resp.status_code in (403, 404)


def test_process_missing_file(client):
    resp = client.post("/process", json={"filename": "x.csv", "analysis_type": "correlation"})
    data = resp.get_json()
    assert data["status"] == "error"


def test_upload_rejects_bad_extension(client):
    import io
    data = {"file": (io.BytesIO(b"junk"), "evil.exe")}
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    body = resp.get_json()
    assert body["status"] == "error"
