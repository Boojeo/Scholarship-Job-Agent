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
    _migrate(conn)
    return conn


# Columns added after the first release; older databases get them on open.
_ADDED_COLUMNS = {"opportunities": {"missing_documents": "TEXT", "ielts_upfront": "INTEGER DEFAULT 0"}}


def _migrate(conn: sqlite3.Connection) -> None:
    for table, cols in _ADDED_COLUMNS.items():
        have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for name, ddl in cols.items():
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


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


def set_fields(conn: sqlite3.Connection, direct_url: str, **fields) -> None:
    """Update extra columns of an opportunity identified by its URL (score, why, status...)."""
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE opportunities SET {cols} WHERE url_hash = ?",  # noqa: S608 - keys are code-defined
                 (*fields.values(), url_hash(direct_url)))


def mark_seen(conn: sqlite3.Connection, key: str, source: str) -> bool:
    """Returns True if the key was new."""
    cur = conn.execute("INSERT OR IGNORE INTO seen_items(item_key, source) VALUES (?, ?)", (key, source))
    return cur.rowcount == 1


def get_kv(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings_kv WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def set_kv(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT INTO settings_kv(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                 (key, value))
