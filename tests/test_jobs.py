"""The SQLite job store: state transitions, blobs, and reaping."""
import pytest

import jobs


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "DB_PATH", tmp_path / "jobs.sqlite")
    monkeypatch.setattr(jobs, "RESULT_DIR", tmp_path)
    monkeypatch.setattr(jobs, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(jobs, "DOWNLOAD_DIR", tmp_path / "downloads")
    (tmp_path / "uploads").mkdir()
    (tmp_path / "downloads").mkdir()
    jobs.init()


def test_lifecycle():
    job_id = jobs.create("tree", "queued up")
    assert jobs.get(job_id)["state"] == "queued"

    jobs.progress(job_id, 0.5, "halfway")
    job = jobs.get(job_id)
    assert (job["state"], job["progress"], job["message"]) == ("running", 0.5, "halfway")

    jobs.finish(job_id, {"download": "x.nw"})
    job = jobs.get(job_id)
    assert job["state"] == "done" and job["result"] == {"download": "x.nw"}


def test_failure_records_the_error():
    job_id = jobs.create("allvsall")
    jobs.fail(job_id, ValueError("bad matrix"))
    assert jobs.get(job_id)["state"] == "failed"
    assert "bad matrix" in jobs.get(job_id)["error"]


def test_unknown_job_is_none():
    assert jobs.get("does-not-exist") is None


def test_update_rejects_unknown_fields():
    job_id = jobs.create("tree")
    with pytest.raises(ValueError):
        jobs.update(job_id, nonsense=1)


def test_blob_roundtrip_and_missing():
    blob_id = jobs.store_blob({"nodes": ["a", "b"]})
    assert jobs.load_blob(blob_id) == {"nodes": ["a", "b"]}
    assert jobs.load_blob("nope") is None


def test_reap_expires_old_jobs_and_their_blobs(monkeypatch):
    monkeypatch.setattr(jobs, "JOB_TTL_SECONDS", 0)
    job_id = jobs.create("allvsall")
    blob_id = jobs.store_blob({"x": 1})
    jobs.finish(job_id, {"blob": blob_id})

    expired, _, _ = jobs.reap(now=jobs.time.time() + 10)
    assert expired == 1
    assert jobs.get(job_id) is None
    assert jobs.load_blob(blob_id) is None      # the blob went with it


def test_reap_fails_jobs_whose_worker_vanished():
    job_id = jobs.create("tree")
    jobs.progress(job_id, 0.2, "working")
    _, stranded, _ = jobs.reap(now=jobs.time.time() + jobs.STALE_RUNNING_SECONDS + 1)
    assert stranded == 1
    assert jobs.get(job_id)["state"] == "failed"


def test_reap_sweeps_stale_uploads_and_downloads(monkeypatch):
    """Uploads and generated results used to accumulate forever."""
    import os
    monkeypatch.setattr(jobs, "JOB_TTL_SECONDS", 3600)
    old = jobs.UPLOAD_DIR / "old.csv"
    old.write_text("x")
    os.utime(old, (0, 0))                       # ancient
    fresh = jobs.DOWNLOAD_DIR / "fresh.nw"
    fresh.write_text("(a,b);")

    _, _, removed = jobs.reap(now=jobs.time.time())
    assert removed == 1
    assert not old.exists()
    assert fresh.exists()                       # inside the retention window
