from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from src.utils.urls import url_hash

from .models import SCHEMA


def connect(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def session(path: Path | str) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_source(conn: sqlite3.Connection, *, name: str, type: str, url: str, origin: str = "seed",
                  region: str | None = None, category: str | None = None, access_method: str | None = None,
                  scraping_notes: str | None = None, language: str | None = None, quality: int | None = None,
                  verification: str = "unchecked", enabled: bool = True) -> bool:
    """Insert a monitored source; returns True if it was new. Existing rows keep their yield stats."""
    h = url_hash(url)
    cur = conn.execute("SELECT id FROM discovered_sources WHERE url_hash = ?", (h,))
    if cur.fetchone():
        conn.execute("UPDATE discovered_sources SET verification = ? WHERE url_hash = ? AND verification = 'unchecked'",
                     (verification, h))
        return False
    conn.execute(
        """INSERT INTO discovered_sources
           (url_hash, name, type, url, region, category, access_method, scraping_notes, language, quality,
            enabled, verification, origin)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (h, name, type, url, region, category, access_method, scraping_notes, language, quality,
         int(enabled), verification, origin),
    )
    return True


def upsert_opportunity(conn: sqlite3.Connection, *, category: str, title: str, direct_url: str,
                       organization: str | None = None, location: str | None = None, deadline: str | None = None,
                       funding: str | None = None, moi_accepted: str | None = None, gre_required: str | None = None,
                       notes: str | None = None, source: str = "unknown", verification: str = "unchecked") -> bool:
    """Insert an opportunity; returns True if it was new (duplicates only refresh `last_seen`)."""
    h = url_hash(direct_url)
    if conn.execute("SELECT 1 FROM opportunities WHERE url_hash = ?", (h,)).fetchone():
        conn.execute("UPDATE opportunities SET last_seen = CURRENT_TIMESTAMP WHERE url_hash = ?", (h,))
        return False
    conn.execute(
        """INSERT INTO opportunities
           (url_hash, category, title, organization, location, direct_url, deadline, funding, moi_accepted,
            gre_required, notes, source, verification)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (h, category, title, organization, location, direct_url, deadline, funding, moi_accepted,
         gre_required, notes, source, verification),
    )
    return True


def count(conn: sqlite3.Connection, table: str, where: str = "1=1", params: tuple = ()) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0]  # noqa: S608
