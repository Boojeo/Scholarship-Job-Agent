from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from . import db


def load_seed(conn: sqlite3.Connection, path: Path) -> int:
    """Insert config/sources_seed.yaml into discovered_sources. Returns how many were new."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    added = 0
    for s in data.get("sources", []):
        added += db.upsert_source(
            conn, name=s["name"], type=s["type"], url=s["url"], origin="seed", region=s.get("region"),
            category=s.get("category"), access_method=s.get("access") or s.get("access_method"),
            enabled=s.get("access") not in ("login_required", "browser_needed", "js_required"),
            scraping_notes=s.get("notes"),
        )
    return added
