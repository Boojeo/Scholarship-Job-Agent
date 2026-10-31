"""Daily monitor: read every enabled source, keep unseen posts, filter, screen with the LLM, store opportunities."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field

import httpx

from src.database import db
from src.llm.base import LLM
from src.monitor.readers import RawItem, Source, new_client, read_source
from src.monitor.screen import keyword_filter, screen
from src.research import web
from src.research.queries import QUERIES
from src.settings import Settings

log = logging.getLogger(__name__)
BLOCKED_HOSTS = ("bayt.com", "gulftalent.com", "naukrigulf.com", "wuzzuf.net", "indeed.com", "jadarat.sa",
                 "findaphd.com", "mastersportal.com", "scholarshipportal.com")
CATEGORIES = ("CATEGORY_1_SCHOLARSHIP", "CATEGORY_2_COOP_PARTTIME", "CATEGORY_3_FULLTIME")
FALLBACK_TASK = {"CATEGORY_1_SCHOLARSHIP": "A", "CATEGORY_2_COOP_PARTTIME": "B", "CATEGORY_3_FULLTIME": "C"}


@dataclass
class MonitorReport:
    sources_read: int = 0
    items_seen: int = 0
    items_new: int = 0
    after_keywords: int = 0
    kept: int = 0
    stored_new: int = 0
    per_category: dict[str, int] = field(default_factory=dict)
    fallback_used: list[str] = field(default_factory=list)

    def summary(self) -> str:
        cats = ", ".join(f"{k.split('_', 2)[-1].lower()}: {v}" for k, v in self.per_category.items())
        fb = f"; fallback search for {', '.join(self.fallback_used)}" if self.fallback_used else ""
        return (f"read {self.sources_read} sources, {self.items_new} new posts of {self.items_seen}, "
                f"{self.after_keywords} passed keywords, {self.kept} matched, {self.stored_new} new opportunities "
                f"({cats}){fb}")


def _reader_type(row) -> str | None:
    url, typ, access = row["url"], (row["type"] or "").lower(), (row["access_method"] or "").lower()
    if any(h in url for h in BLOCKED_HOSTS) or access in ("browser_needed", "login_required", "js_required"):
        return None
    if "t.me/" in url:
        return "telegram"
    if typ == "rss" or url.rstrip("/").endswith(("feed", ".rss", ".xml")) or "/rss" in url:
        return "rss"
    if typ in ("json_api", "api"):
        return "json_api"
    if typ in ("x_account", "youtube"):
        return None
    return "html"


def load_sources(conn) -> list[Source]:
    out = []
    for row in conn.execute("SELECT * FROM discovered_sources WHERE enabled = 1"):
        kind = _reader_type(row)
        if not kind:
            continue
        url = row["url"]
        if kind == "telegram" and "/s/" not in url:
            url = "https://t.me/s/" + url.rstrip("/").split("/")[-1].lstrip("@")
        out.append(Source(row["name"], kind, url, row["category"] or "CATEGORY_1_SCHOLARSHIP"))
    return out


def _key(item: RawItem) -> str:
    return hashlib.sha1(f"{item.source}|{item.key}".encode()).hexdigest()


async def _read_all(sources: list[Source], transport=None) -> list[RawItem]:
    async with new_client(transport) as client:
        results = await asyncio.gather(*(read_source(client, s) for s in sources))
    return [it for batch in results for it in batch]


def _search_items(category: str, search_fn, max_queries: int = 4) -> list[RawItem]:
    hits = web.collect_hits(QUERIES[FALLBACK_TASK[category]][:max_queries], search_fn, per_query=6)
    return [RawItem("web search", category, f"search:{h.url}", h.title, h.snippet, h.url) for h in hits]


class Monitor:
    def __init__(self, llm: LLM, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None,
                 search_fn=web.ddg_search, fallback: bool = True):
        self.llm, self.settings, self.transport = llm, settings, transport
        self.search_fn, self.fallback = search_fn, fallback

    def run(self, only_category: str | None = None) -> MonitorReport:
        rep = MonitorReport()
        with db.session(self.settings.db_path) as conn:
            sources = [s for s in load_sources(conn) if not only_category or s.category == only_category]
            rep.sources_read = len(sources)
            items = asyncio.run(_read_all(sources, self.transport))
            rep.items_seen = len(items)
            fresh = [it for it in items if db.mark_seen(conn, _key(it), it.source)]
            conn.commit()
            rep.items_new = len(fresh)
            candidates = [it for it in fresh if keyword_filter(it)]
            rep.after_keywords = len(candidates)
            rep.stored_new = self._screen_and_store(conn, candidates, rep)

            if self.fallback:
                for cat in CATEGORIES:
                    if only_category and cat != only_category:
                        continue
                    if rep.per_category.get(cat, 0) >= 3:
                        continue
                    extra = [it for it in _search_items(cat, self.search_fn)
                             if db.mark_seen(conn, _key(it), it.source)]
                    if extra:
                        rep.fallback_used.append(cat.split("_", 2)[-1].lower())
                        rep.stored_new += self._screen_and_store(conn, extra, rep)
            db.set_kv(conn, "last_monitor_run", time.strftime("%Y-%m-%d %H:%M"))
            db.set_kv(conn, "last_monitor_summary", rep.summary())
        log.info("monitor: %s", rep.summary())
        return rep

    def _screen_and_store(self, conn, candidates: list[RawItem], rep: MonitorReport) -> int:
        stored = 0
        for item, res in screen(self.llm, candidates):
            rep.kept += 1
            url = res.official_url if res.official_url.startswith("http") else item.url
            if not url.startswith("http"):
                continue
            new = db.upsert_opportunity(
                conn, category=res.category, title=res.title or item.title, direct_url=url,
                organization=res.organization, location=res.location, deadline=res.deadline, funding=res.funding,
                moi_accepted=res.moi_accepted, gre_required=res.gre_required, notes=item.text[:1500],
                source=f"monitor:{item.source}", verification="unchecked")
            if new:
                db.set_fields(conn, url, match_score=res.match_score, why_it_matches=res.why_it_matches,
                              missing_documents=json.dumps(res.missing_documents),
                              ielts_upfront=int(res.ielts_required_upfront))
                stored += 1
                if res.match_score >= self.settings.match_threshold:
                    rep.per_category[res.category] = rep.per_category.get(res.category, 0) + 1
        conn.commit()
        return stored
