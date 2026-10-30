"""Free web access for the research step: DuckDuckGo search + page download + text extraction."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from src.utils.urls import normalize_url

log = logging.getLogger(__name__)
UA = "Mozilla/5.0 (compatible; career-autopilot/0.1; personal research)"
# Pages that need a login or can't be read as text. Their search snippets are still kept.
UNFETCHABLE = ("linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "tiktok.com",
               "pinterest.", "quora.com", "reddit.com", "youtube.com", "youtu.be")


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


SearchFn = Callable[[str, int], list[SearchHit]]


def ddg_search(query: str, max_results: int = 8) -> list[SearchHit]:
    """DuckDuckGo text search. Returns [] (and logs) when blocked or offline."""
    try:
        from ddgs import DDGS

        rows = DDGS().text(query, max_results=max_results) or []
    except Exception as exc:  # the library raises many different errors on rate limits
        log.warning("search failed for %r: %s", query, str(exc)[:120])
        return []
    return [SearchHit(r.get("title", ""), r.get("href", ""), r.get("body", "")) for r in rows if r.get("href")]


def is_fetchable(url: str) -> bool:
    host = urlsplit(url).netloc.lower()
    return url.startswith("http") and not any(bad in host for bad in UNFETCHABLE)


def html_to_text(html: str, base_url: str, max_chars: int = 9000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()
    links, seen = [], set()
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ").split())
        href = urljoin(base_url, a["href"])
        if len(text) >= 4 and href.startswith("http") and href not in seen:
            seen.add(href)
            links.append(f"- {text[:80]} -> {href}")
    body = re.sub(r"\n\s*\n+", "\n", soup.get_text("\n"))
    body = "\n".join(line.strip() for line in body.splitlines() if line.strip())
    link_block = "\nLINKS ON PAGE:\n" + "\n".join(links[:30]) if links else ""
    return (body[: max_chars - len(link_block[:1500])] + link_block[:1500]).strip()


async def fetch_pages(urls: list[str], *, concurrency: int = 6, timeout: float = 20.0, max_chars: int = 9000,
                      transport: httpx.AsyncBaseTransport | None = None) -> dict[str, str]:
    sem = asyncio.Semaphore(concurrency)
    out: dict[str, str] = {}

    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=timeout, follow_redirects=True,
                                 transport=transport) as client:
        async def one(url: str):
            async with sem:
                try:
                    r = await client.get(url)
                except httpx.HTTPError:
                    return
            if r.status_code >= 400 or "html" not in r.headers.get("content-type", "html"):
                return
            text = html_to_text(r.text, str(r.url), max_chars)
            if len(text) > 400:
                out[url] = text

        await asyncio.gather(*(one(u) for u in urls))
    return out


def collect_hits(queries: list[str], search: SearchFn, *, per_query: int = 8, delay: float = 1.5,
                 sleep: Callable[[float], None] = time.sleep) -> list[SearchHit]:
    """Run every query, dedupe by normalised URL, keep order (earlier queries first)."""
    seen: set[str] = set()
    hits: list[SearchHit] = []
    for q in queries:
        for hit in search(q, per_query):
            key = normalize_url(hit.url)
            if key not in seen:
                seen.add(key)
                hits.append(hit)
        sleep(delay)
    return hits
