"""Read the curated sources (config/sources.yaml). One small reader per source type; all return RawItem."""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

import feedparser
import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
MAX_ITEMS_PER_SOURCE = 25


@dataclass
class Source:
    name: str
    type: str          # telegram | rss | json_api | html
    url: str
    category: str
    region: str = ""
    access: str = ""
    notes: str = ""


@dataclass
class RawItem:
    source: str
    category_hint: str
    key: str           # stable id used for "seen before?"
    title: str
    text: str
    url: str
    published: str = ""
    links: list[str] = field(default_factory=list)


def _clean(html_or_text: str, limit: int = 1500) -> str:
    text = BeautifulSoup(html_or_text or "", "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()[:limit]


# ---------------------------------------------------------------------------------------------- telegram
def parse_telegram(html: str, src: Source) -> list[RawItem]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for msg in soup.select(".tgme_widget_message[data-post]"):
        post = msg["data-post"]
        body = msg.select_one(".tgme_widget_message_text")
        if not body:
            continue
        text = re.sub(r"\s+", " ", body.get_text(" ")).strip()
        links = [a["href"] for a in body.select("a[href]") if a["href"].startswith("http")
                 and "t.me/" not in a["href"]]
        when = msg.select_one("time[datetime]")
        items.append(RawItem(
            source=src.name, category_hint=src.category, key=f"tg:{post}", title=text[:120], text=text[:1500],
            url=links[0] if links else f"https://t.me/{post}", published=when["datetime"] if when else "",
            links=links[:5],
        ))
    return items[-MAX_ITEMS_PER_SOURCE:]


# ---------------------------------------------------------------------------------------------- rss
def parse_rss(content: bytes, src: Source) -> list[RawItem]:
    feed = feedparser.parse(content)
    items = []
    for e in feed.entries[:MAX_ITEMS_PER_SOURCE]:
        link = e.get("link", "")
        if not link:
            continue
        items.append(RawItem(
            source=src.name, category_hint=src.category, key=f"rss:{e.get('id') or link}",
            title=_clean(e.get("title", ""), 200), text=_clean(e.get("summary", ""), 1500), url=link,
            published=e.get("published", ""),
        ))
    return items


# ---------------------------------------------------------------------------------------------- json feeds
TECH_WORDS = re.compile(r"\b(ai|ml|machine learning|deep learning|data|software|developer|engineer|python|nlp|"
                        r"computer vision|research|backend|full[- ]?stack|llm)\b", re.I)


def parse_json(content: bytes, src: Source, now: dt.datetime | None = None) -> list[RawItem]:
    data = json.loads(content)
    host = urlsplit(src.url).netloc
    now = now or dt.datetime.now(dt.timezone.utc)
    rows: list[RawItem] = []
    if "githubusercontent.com" in host:  # SimplifyJobs trackers: huge list, keep recent tech roles
        cutoff = (now - dt.timedelta(days=3)).timestamp()
        for r in data:
            if not r.get("active", True) or not r.get("is_visible", True) or r.get("date_posted", 0) < cutoff:
                continue
            if not TECH_WORDS.search(r.get("title", "")):
                continue
            rows.append(RawItem(src.name, src.category, f"simplify:{r.get('id') or r.get('url')}",
                                f"{r.get('title')} at {r.get('company_name')}",
                                f"{r.get('title')} | {r.get('company_name')} | {', '.join(r.get('locations', []))} | "
                                f"sponsorship: {r.get('sponsorship', 'unknown')}", r.get("url", ""),
                                str(r.get("date_posted", ""))))
    elif "remoteok" in host:
        for r in data[1:]:
            if not TECH_WORDS.search(r.get("position", "")):
                continue
            rows.append(RawItem(src.name, src.category, f"remoteok:{r.get('id')}",
                                f"{r.get('position')} at {r.get('company')}",
                                _clean(f"{r.get('position')} | {r.get('company')} | {r.get('location', '')} | "
                                       f"{' '.join(r.get('tags', []))} | {r.get('description', '')}", 1200),
                                r.get("url", ""), r.get("date", "")))
    elif "arbeitnow" in host:
        for r in data.get("data", []):
            if not TECH_WORDS.search(r.get("title", "")):
                continue
            rows.append(RawItem(src.name, src.category, f"arbeitnow:{r.get('slug') or r.get('url')}",
                                f"{r.get('title')} at {r.get('company_name')}",
                                _clean(f"{r.get('title')} | {r.get('company_name')} | {r.get('location')} | "
                                       f"remote: {r.get('remote')} | {r.get('description', '')}", 1200),
                                r.get("url", ""), str(r.get("created_at", ""))))
    else:
        log.warning("no JSON adapter for %s", src.url)
    return rows[:MAX_ITEMS_PER_SOURCE * 2]


# ---------------------------------------------------------------------------------------------- html pages
def parse_html(html: str, src: Source) -> list[RawItem]:
    """Program/listing pages without a feed: every specific link on the page is a candidate item."""
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlsplit(src.url).netloc
    items, seen = [], set()
    for a in soup.select("a[href]"):
        text = re.sub(r"\s+", " ", a.get_text(" ")).strip()
        href = urljoin(src.url, a["href"]).split("#")[0]
        parts = urlsplit(href)
        if len(text) < 15 or not href.startswith("http") or href in seen:
            continue
        if parts.netloc != base_host or len([p for p in parts.path.split("/") if p]) < 2:
            continue
        seen.add(href)
        items.append(RawItem(src.name, src.category, f"html:{href}", text[:150], text, href))
    return items[:MAX_ITEMS_PER_SOURCE]


async def read_source(client: httpx.AsyncClient, src: Source) -> list[RawItem]:
    try:
        r = await client.get(src.url, timeout=60 if "scholarship-positions" in src.url else 30)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("source %s unreachable: %s", src.name, (str(exc).splitlines() or [type(exc).__name__])[0][:120])
        return []
    try:
        if src.type == "telegram":
            return parse_telegram(r.text, src)
        if src.type == "rss":
            return parse_rss(r.content, src)
        if src.type == "json_api":
            return parse_json(r.content, src)
        return parse_html(r.text, src)
    except Exception as exc:  # one broken source must never stop the daily run
        log.warning("source %s could not be parsed: %s", src.name, str(exc)[:120])
        return []


def new_client(transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, transport=transport,
                             limits=httpx.Limits(max_connections=8))
