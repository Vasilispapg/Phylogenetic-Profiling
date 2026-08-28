"""
Per-client rate limiting and banning.

nginx limits requests at the edge in production (docs/DEPLOY.md), but the app
should not depend on being deployed behind it: this is the same defence one
layer in, and it is the layer that knows which requests are *expensive*.

Two budgets, because the traffic has two shapes. Submitting work — an upload, a
job — is rare and costly. Polling a running job is frequent and nearly free: a
client asks every two seconds, so one budget for both would throttle a single
honest user.

A client that keeps overrunning the expensive budget collects strikes, and
enough strikes earn a temporary ban that doubles each time. State lives in the
same SQLite database as the jobs, so the limits hold across gunicorn workers
instead of being four times looser than they look.
"""
import logging
import sqlite3
import time
from dataclasses import dataclass

import config
import jobs

log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
  ip           TEXT PRIMARY KEY,
  window_start REAL NOT NULL,
  heavy        INTEGER NOT NULL DEFAULT 0,
  api          INTEGER NOT NULL DEFAULT 0,
  strikes      INTEGER NOT NULL DEFAULT 0,
  banned_until REAL NOT NULL DEFAULT 0,
  updated      REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS clients_updated ON clients (updated);
"""

WINDOW = 60.0
BUDGETS = {"heavy": lambda: config.RATE_HEAVY_PER_MIN, "api": lambda: config.RATE_API_PER_MIN}


@dataclass
class Verdict:
    allowed: bool
    retry_after: int = 0
    reason: str = ""


def init():
    """Create the client table. Idempotent."""
    with jobs._connect() as con:                                  # noqa: SLF001
        con.executescript(_SCHEMA)


def client_ip(request):
    """
    The address to hold responsible.

    ``X-Forwarded-For`` is only believed when TRUSTED_PROXY says something is
    actually in front of us; otherwise anyone could set the header and rotate
    their way out of every limit.
    """
    if config.TRUSTED_PROXY:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    return (request.remote_addr or "unknown")[:64]


def check(ip, bucket):
    """Count this request against ``bucket`` and say whether it may proceed."""
    if not config.RATE_LIMIT_ENABLED:
        return Verdict(True)

    now = time.time()
    limit = BUDGETS[bucket]()
    try:
        with jobs._connect() as con:                              # noqa: SLF001
            row = con.execute(
                "SELECT window_start, heavy, api, strikes, banned_until "
                "FROM clients WHERE ip = ?", (ip,)
            ).fetchone()

            if row is None:
                con.execute(
                    "INSERT INTO clients (ip, window_start, heavy, api, updated) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (ip, now, int(bucket == "heavy"), int(bucket == "api"), now),
                )
                return Verdict(True)

            window_start, heavy, api, strikes, banned_until = row
            if banned_until > now:
                return Verdict(False, int(banned_until - now) + 1,
                               "Too many requests; this address is temporarily blocked.")

            if now - window_start >= WINDOW:
                window_start, heavy, api = now, 0, 0

            counts = {"heavy": heavy, "api": api}
            counts[bucket] += 1

            if counts[bucket] > limit:
                strikes += 1
                ban_for = 0.0
                if strikes >= config.BAN_AFTER_STRIKES:
                    over = strikes - config.BAN_AFTER_STRIKES
                    ban_for = min(config.BAN_SECONDS * (2 ** over), config.BAN_SECONDS_MAX)
                    log.warning("banning %s for %.0fs (%d strikes)", ip, ban_for, strikes)
                con.execute(
                    "UPDATE clients SET window_start=?, heavy=?, api=?, strikes=?, "
                    "banned_until=?, updated=? WHERE ip=?",
                    (window_start, counts["heavy"], counts["api"], strikes,
                     now + ban_for if ban_for else 0, now, ip),
                )
                retry = int(ban_for) + 1 if ban_for else int(WINDOW - (now - window_start)) + 1
                return Verdict(False, retry, "Too many requests. Slow down and try again.")

            con.execute(
                "UPDATE clients SET window_start=?, heavy=?, api=?, updated=? WHERE ip=?",
                (window_start, counts["heavy"], counts["api"], now, ip),
            )
            return Verdict(True)
    except sqlite3.Error:
        # A limiter that fails closed would take the site down with it.
        log.exception("rate limiter unavailable; allowing the request")
        return Verdict(True)


def strike(ip, reason):
    """
    Record that a client sent something we refused as malformed or suspicious.

    Rejected uploads cost real work — the file is streamed and inspected — so a
    client producing them repeatedly is treated like one exceeding the budget.
    """
    if not config.RATE_LIMIT_ENABLED:
        return
    now = time.time()
    log.info("strike for %s: %s", ip, reason)
    try:
        with jobs._connect() as con:                              # noqa: SLF001
            con.execute(
                "INSERT INTO clients (ip, window_start, strikes, updated) VALUES (?, ?, 1, ?) "
                "ON CONFLICT(ip) DO UPDATE SET strikes = strikes + 1, updated = ?",
                (ip, now, now, now),
            )
            strikes = con.execute("SELECT strikes FROM clients WHERE ip = ?", (ip,)).fetchone()[0]
            if strikes >= config.BAN_AFTER_STRIKES:
                over = strikes - config.BAN_AFTER_STRIKES
                ban_for = min(config.BAN_SECONDS * (2 ** over), config.BAN_SECONDS_MAX)
                con.execute("UPDATE clients SET banned_until = ? WHERE ip = ?",
                            (now + ban_for, ip))
                log.warning("banning %s for %.0fs after %d strikes", ip, ban_for, strikes)
    except sqlite3.Error:
        log.exception("could not record a strike for %s", ip)


def forget_old(now=None):
    """Drop clients that have been quiet for a day, so the table stays small."""
    now = time.time() if now is None else now
    try:
        with jobs._connect() as con:                              # noqa: SLF001
            return con.execute(
                "DELETE FROM clients WHERE updated < ? AND banned_until < ?",
                (now - 86400, now),
            ).rowcount
    except sqlite3.Error:
        log.exception("could not prune the client table")
        return 0
