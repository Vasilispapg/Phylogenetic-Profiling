"""
Rate limiting, strikes and bans.

The limiter is off for the rest of the suite (it would throttle the tests
themselves), so it is switched on deliberately here.
"""
import io

import pytest

import config
import guard
import jobs
from app import app as flask_app


@pytest.fixture(autouse=True)
def limiter_on(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "DB_PATH", tmp_path / "jobs.sqlite")
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(guard.config, "RATE_LIMIT_ENABLED", True)
    jobs.init()
    guard.init()


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


MATRIX = b"Species,D1,D2\ns1,1,0\ns2,0,1\n"


# --------------------------------------------------------------------------- #
# Budgets
# --------------------------------------------------------------------------- #
def test_requests_are_allowed_up_to_the_budget(monkeypatch):
    monkeypatch.setattr(config, "RATE_HEAVY_PER_MIN", 3)
    for _ in range(3):
        assert guard.check("1.2.3.4", "heavy").allowed
    verdict = guard.check("1.2.3.4", "heavy")
    assert not verdict.allowed
    assert verdict.retry_after > 0
    assert "Slow down" in verdict.reason


def test_the_two_budgets_are_independent(monkeypatch):
    """Polling a job must not be throttled by having submitted one."""
    monkeypatch.setattr(config, "RATE_HEAVY_PER_MIN", 1)
    monkeypatch.setattr(config, "RATE_API_PER_MIN", 50)
    assert guard.check("5.6.7.8", "heavy").allowed
    assert not guard.check("5.6.7.8", "heavy").allowed
    for _ in range(40):
        assert guard.check("5.6.7.8", "api").allowed


def test_clients_are_counted_separately(monkeypatch):
    monkeypatch.setattr(config, "RATE_HEAVY_PER_MIN", 1)
    assert guard.check("9.9.9.9", "heavy").allowed
    assert guard.check("8.8.8.8", "heavy").allowed


def test_the_window_rolls_over(monkeypatch):
    monkeypatch.setattr(config, "RATE_HEAVY_PER_MIN", 1)
    assert guard.check("7.7.7.7", "heavy").allowed
    assert not guard.check("7.7.7.7", "heavy").allowed
    with jobs._connect() as con:
        con.execute("UPDATE clients SET window_start = window_start - ? WHERE ip = ?",
                    (guard.WINDOW + 1, "7.7.7.7"))
    assert guard.check("7.7.7.7", "heavy").allowed


# --------------------------------------------------------------------------- #
# Strikes and bans
# --------------------------------------------------------------------------- #
def test_enough_strikes_earn_a_ban(monkeypatch):
    monkeypatch.setattr(config, "BAN_AFTER_STRIKES", 3)
    monkeypatch.setattr(config, "BAN_SECONDS", 60)
    for _ in range(3):
        guard.strike("4.4.4.4", "rejected upload")
    verdict = guard.check("4.4.4.4", "api")
    assert not verdict.allowed
    assert "temporarily blocked" in verdict.reason
    assert verdict.retry_after > 0


def test_bans_lengthen_with_repetition(monkeypatch):
    monkeypatch.setattr(config, "BAN_AFTER_STRIKES", 2)
    monkeypatch.setattr(config, "BAN_SECONDS", 100)
    guard.strike("3.3.3.3", "x"); guard.strike("3.3.3.3", "x")
    first = guard.check("3.3.3.3", "api").retry_after
    guard.strike("3.3.3.3", "x")
    second = guard.check("3.3.3.3", "api").retry_after
    assert second > first


def test_a_ban_is_capped(monkeypatch):
    monkeypatch.setattr(config, "BAN_AFTER_STRIKES", 1)
    monkeypatch.setattr(config, "BAN_SECONDS", 100)
    monkeypatch.setattr(config, "BAN_SECONDS_MAX", 300)
    for _ in range(12):
        guard.strike("2.2.2.2", "x")
    assert guard.check("2.2.2.2", "api").retry_after <= 301


# --------------------------------------------------------------------------- #
# Which address gets the blame
# --------------------------------------------------------------------------- #
def test_forwarded_headers_are_ignored_without_a_trusted_proxy(monkeypatch):
    """Otherwise anyone could rotate the header and never hit a limit."""
    monkeypatch.setattr(config, "TRUSTED_PROXY", False)
    with flask_app.test_request_context("/api/health",
                                        headers={"X-Forwarded-For": "6.6.6.6"},
                                        environ_base={"REMOTE_ADDR": "10.0.0.1"}):
        from flask import request
        assert guard.client_ip(request) == "10.0.0.1"


def test_forwarded_headers_are_used_behind_a_trusted_proxy(monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXY", True)
    with flask_app.test_request_context("/api/health",
                                        headers={"X-Forwarded-For": "6.6.6.6, 10.0.0.1"},
                                        environ_base={"REMOTE_ADDR": "10.0.0.1"}):
        from flask import request
        assert guard.client_ip(request) == "6.6.6.6"


# --------------------------------------------------------------------------- #
# End to end through the app
# --------------------------------------------------------------------------- #
def test_the_endpoint_returns_429_with_retry_after(client, monkeypatch):
    monkeypatch.setattr(config, "RATE_HEAVY_PER_MIN", 2)
    codes = []
    for _ in range(4):
        resp = client.post("/api/matrices",
                           data={"file": (io.BytesIO(MATRIX), "m.csv")},
                           content_type="multipart/form-data")
        codes.append(resp.status_code)
    assert 429 in codes
    limited = [r for r in codes if r == 429]
    assert len(limited) >= 1
    resp = client.post("/api/matrices", data={"file": (io.BytesIO(MATRIX), "m.csv")},
                       content_type="multipart/form-data")
    if resp.status_code == 429:
        assert resp.headers["Retry-After"].isdigit()
        assert resp.get_json()["status"] == "error"


def test_a_rejected_upload_counts_as_a_strike(client, monkeypatch):
    """Inspecting a bad file costs work, so sending them repeatedly is charged."""
    monkeypatch.setattr(config, "BAN_AFTER_STRIKES", 100)   # isolate the strike count
    before = _strikes()
    client.post("/api/matrices",
                data={"file": (io.BytesIO(b"\x00\x01binary"), "m.csv")},
                content_type="multipart/form-data")
    assert _strikes() > before


def test_polling_is_not_throttled_by_the_heavy_budget(client, monkeypatch):
    monkeypatch.setattr(config, "RATE_HEAVY_PER_MIN", 1)
    monkeypatch.setattr(config, "RATE_API_PER_MIN", 100)
    client.post("/api/matrices", data={"file": (io.BytesIO(MATRIX), "m.csv")},
                content_type="multipart/form-data")
    for _ in range(30):
        assert client.get("/api/health").status_code == 200


def test_the_spa_is_never_rate_limited(client, monkeypatch):
    """A limiter that can lock someone out of the page itself is a bad limiter."""
    monkeypatch.setattr(config, "RATE_API_PER_MIN", 1)
    for _ in range(10):
        assert client.get("/").status_code in (200, 503)


def _strikes():
    with jobs._connect() as con:
        row = con.execute("SELECT COALESCE(SUM(strikes), 0) FROM clients").fetchone()
    return row[0]
