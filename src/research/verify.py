"""Check that URLs found by the research LLM really exist. LLM output is never trusted blindly."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

import httpx

UA = "Mozilla/5.0 (compatible; career-autopilot/0.1; personal research)"
_WORD = re.compile(r"[a-z0-9]{4,}")


@dataclass
class UrlCheck:
    url: str
    verdict: str  # verified | blocked | dead
    status: int | None = None
    final_url: str | None = None
    title_match: float | None = None


async def _check_one(client: httpx.AsyncClient, url: str, hint: str, sem: asyncio.Semaphore) -> UrlCheck:
    async with sem:
        try:
            r = await client.get(url)
        except httpx.HTTPError:
            return UrlCheck(url, "dead")
    if r.status_code in (401, 403, 429, 999):  # bot walls: the page exists but won't talk to us
        return UrlCheck(url, "blocked", r.status_code, str(r.url))
    if r.status_code >= 400:
        return UrlCheck(url, "dead", r.status_code, str(r.url))
    match = None
    words = set(_WORD.findall(hint.lower()))
    if words and "text" in r.headers.get("content-type", ""):
        page = r.text[:300_000].lower()
        match = sum(w in page for w in words) / len(words)
    return UrlCheck(url, "verified", r.status_code, str(r.url), match)


async def check_urls(items: list[tuple[str, str]], *, concurrency: int = 8, timeout: float = 15.0,
                     transport: httpx.AsyncBaseTransport | None = None) -> dict[str, UrlCheck]:
    """items: (url, hint_text) pairs; hint is matched against the page to catch hallucinated links."""
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=timeout, follow_redirects=True,
                                 transport=transport) as client:
        results = await asyncio.gather(*(_check_one(client, u, hint, sem) for u, hint in items))
    return {c.url: c for c in results}
