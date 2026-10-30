from __future__ import annotations

import hashlib
from urllib.parse import urlsplit, urlunsplit

_TRACKING = ("utm_", "fbclid", "gclid", "ref=")


def normalize_url(url: str) -> str:
    """Lowercase host, drop fragments, tracking params and trailing slash so duplicates collide."""
    parts = urlsplit(url.strip())
    query = "&".join(p for p in parts.query.split("&") if p and not p.lower().startswith(_TRACKING))
    path = parts.path.rstrip("/") or ""
    return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), path, query, ""))


def url_hash(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode()).hexdigest()
