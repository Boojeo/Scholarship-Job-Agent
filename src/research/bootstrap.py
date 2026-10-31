"""Automated research bootstrap.

Runs the research prompt through a web-grounded LLM (Gemini), turns the answers into structured rows,
verifies every URL over HTTP, and stores what survives in SQLite plus config/sources_discovered.yaml.
Raw answers are saved so an interrupted run can resume without spending quota again.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import re
import time
from pathlib import Path
from typing import Callable

import yaml
from urllib.parse import urlsplit

from src.database import db
from src.llm.base import LLM, LLMError
from src.research.prompt import ResearchTask, build_tasks
from src.research import web
from src.research.queries import QUERIES
from src.research.schemas import OpportunityItem, SourceItem
from src.research.verify import UrlCheck, check_urls
from src.settings import ROOT, Settings

log = logging.getLogger(__name__)
PROFILE_BRIEF = ("Candidate: Somali national resident in Saudi Arabia and the UAE, B.Sc. Computer Science "
                 "(GPA 4.99/5.0, graduating July 2027), has an English Medium-of-Instruction letter, no IELTS yet, "
                 "no GRE; wants fully funded MS/PhD in AI from 2027, AI/CS internships/co-op, and entry-level AI/CS jobs.")
SYSTEM = ("You are a careful research analyst. Use web search. Only report pages you actually opened. "
          "Mark anything you could not verify as UNVERIFIED. Never invent URLs, deadlines or programs.")
PROMPT_FILE = ROOT / "docs" / "gemini_research_prompt.md"


def _structure_prompt(task: ResearchTask, notes: str) -> str:
    if task.kind == "opportunities":
        fields = ("category (always '%s'), title, organization, location, url, deadline, funding, "
                  "moi_accepted (yes/no/unknown), gre_required (yes/no/unknown), notes" % task.category)
    else:
        fields = ("name, type (portal|job_board|telegram|x_account|youtube|rss|api|other), url, region, category, "
                  "update_frequency, access_method (rss|api|static_html|js_required|login_required), "
                  "scraping_notes, language, quality (1-5 integer)")
    today = dt.date.today().isoformat()
    return (f"Today is {today}. {PROFILE_BRIEF}\n"
            "Convert the research material below into a JSON array. Each element has these fields: "
            f"{fields}.\nRules: include only items that have a real http(s) URL in the material (the page URL "
            "after '### PAGE' or a link shown in it); copy facts exactly, use \"\" or \"unknown\" when the "
            "material does not say; add nothing that is not in the material; drop expired items, pages that are "
            "only generic news, and anything clearly irrelevant to this candidate. If a page lists many "
            "programs, return each as its own item with its own link when one is shown. "
            "The url must be the specific page of that program or posting, never a site homepage, a search or "
            "listing page, or a careers landing page. If the page is a blog or aggregator about a program and "
            "shows a link to the official university/employer page, use the official link as url and mention the "
            "aggregator in notes. Drop programs that only accept people already enrolled in a PhD, that need a "
            "university nomination, or that are not open to a candidate with only a Bachelor's degree. "
            "Return [] if nothing qualifies.\n\nMATERIAL:\n" + notes)


def _chunks(notes: str, max_chars: int = 45_000) -> list[str]:
    """Split page bundles on the '### PAGE' markers so each model call stays small."""
    parts = re.split(r"(?=^### (?:PAGE|SNIPPET) )", notes, flags=re.MULTILINE)
    chunks, cur = [], ""
    for part in parts:
        if cur and len(cur) + len(part) > max_chars:
            chunks.append(cur)
            cur = ""
        cur += part
        while len(cur) > max_chars * 2:  # a single enormous page / unmarked text
            chunks.append(cur[:max_chars])
            cur = cur[max_chars:]
    if cur.strip():
        chunks.append(cur)
    return chunks


GENERIC_PATHS = {"", "careers", "jobs", "search", "research", "about", "blog", "scholarships", "opportunities",
                 "en", "home", "index", "en-us", "programs", "admissions"}
_ORG_STOP = {"university", "institute", "research", "technology", "science", "college", "school", "national"}


def is_generic_url(url: str) -> bool:
    """Site roots, search pages and one-word landing pages are not a specific opportunity."""
    parts = urlsplit(url)
    segments = [p for p in parts.path.lower().split("/") if p]
    if "search" in segments or "search" in parts.query.lower():
        return True
    return len(segments) == 0 or (len(segments) == 1 and segments[0] in GENERIC_PATHS) or \
        (len(segments) == 2 and segments[0] in GENERIC_PATHS and segments[1] in GENERIC_PATHS)


def _org_key(org: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"\(.*?\)", "", org.lower())).strip()


def _deadline_key(deadline: str) -> str:
    m = re.search(r"([A-Za-z]{3,9}\.? \d{1,2},? \d{4}|\d{1,2} [A-Za-z]{3,9} \d{4}|\d{4}-\d{2}-\d{2})", deadline or "")
    return re.sub(r"[^a-z0-9]", "", m.group(1).lower()) if m else ""


def _title_tokens(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", title.lower())} - {"scholarship", "scholarships", "fully", "funded",
                                                                  "program", "programme", "master", "masters",
                                                                  "fellowship", "funding", "with", "from"}


def _official_rank(url: str, org: str) -> int:
    """0 = looks like the organisation's own site, 1 = third party (blog/aggregator)."""
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    if host.endswith((".edu", ".gov")) or ".ac." in host or ".edu." in host or ".gov." in host:
        return 0
    words = {w for w in re.findall(r"[a-z]{4,}", org.lower()) if w not in _ORG_STOP}
    return 0 if any(w in host for w in words) else 1


def dedupe_opportunities(items: list) -> list:
    """Collapse aggregator copies of one program: same organisation and (same deadline or similar title)."""
    kept: list = []
    for item in items:
        for i, other in enumerate(kept):
            same_org = _org_key(item.organization) == _org_key(other.organization) and _org_key(item.organization)
            if not same_org:
                continue
            a, b = _title_tokens(item.title), _title_tokens(other.title)
            same_deadline = _deadline_key(item.deadline) and _deadline_key(item.deadline) == _deadline_key(other.deadline)
            similar = a and b and len(a & b) / len(a | b) >= 0.5
            if same_deadline or similar:
                if _official_rank(item.url, item.organization) < _official_rank(other.url, other.organization):
                    kept[i] = item
                break
        else:
            kept.append(item)
    return kept


class ResearchBootstrap:
    def __init__(self, llm: LLM, settings: Settings, *, run_dir: Path | None = None,
                 prompt_file: Path = PROMPT_FILE, sleep: Callable[[float], None] = time.sleep,
                 url_transport=None, mode: str = "web", search_fn: web.SearchFn = web.ddg_search,
                 pages_per_task: int = 24):
        self.llm = llm
        self.settings = settings
        self.prompt_file = prompt_file
        self.sleep = sleep
        self.url_transport = url_transport
        self.mode = mode                  # "web" = free DuckDuckGo + page download; "grounded" = Gemini Google Search
        self.search_fn = search_fn
        self.pages_per_task = pages_per_task
        stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
        self.run_dir = run_dir or settings.data_dir / "research" / stamp
        self.run_dir.mkdir(parents=True, exist_ok=True)

    # -- step 1: web-grounded research, one call per task -------------------------------------------
    def research(self, only: set[str] | None = None, force: bool = False) -> dict[str, str]:
        answers: dict[str, str] = {}
        for task in build_tasks(self.prompt_file):
            if only and task.key not in only:
                continue
            raw = self.run_dir / f"{task.key}.md"
            if raw.exists() and not force:
                answers[task.key] = raw.read_text(encoding="utf-8")
                log.info("task %s: reusing saved answer", task.key)
                continue
            if self.mode == "web":
                if task.kind == "notes":
                    continue  # the 'traps' checklist is covered by the matcher rules, not by web pages
                log.info("task %s: searching the web...", task.key)
                text = self._web_bundle(task)
                if not text:
                    log.error("task %s: no pages found (search blocked or offline?)", task.key)
                    continue
            else:
                log.info("task %s: researching (Gemini web-grounded)...", task.key)
                try:
                    text = self.llm.generate(task.prompt, system=SYSTEM, tier="research", search=True,
                                             max_tokens=32768, temperature=0.2).text
                except LLMError as exc:
                    log.error("task %s failed: %s", task.key, exc)
                    continue
                self.sleep(self.settings.research_delay_seconds)
            raw.write_text(text, encoding="utf-8")
            answers[task.key] = text
        return answers

    def _web_bundle(self, task: ResearchTask) -> str:
        hits = web.collect_hits(QUERIES.get(task.key, []), self.search_fn, sleep=self.sleep)
        fetchable = [h for h in hits if web.is_fetchable(h.url)][: self.pages_per_task]
        pages = asyncio.run(web.fetch_pages([h.url for h in fetchable], transport=self.url_transport))
        blocks = []
        for h in fetchable:
            if h.url in pages:
                blocks.append(f"### PAGE {h.url}\nTITLE: {h.title}\nSNIPPET: {h.snippet}\n{pages[h.url]}\n")
        # login-walled / social results: keep the snippet only (useful for finding accounts and channels)
        for h in hits:
            if not web.is_fetchable(h.url):
                blocks.append(f"### SNIPPET {h.url}\nTITLE: {h.title}\nSNIPPET: {h.snippet}\n")
        return "\n".join(blocks)

    # -- step 2: free text -> validated rows -----------------------------------------------------------
    def structure(self, answers: dict[str, str]):
        tasks = {t.key: t for t in build_tasks(self.prompt_file)}
        opportunities: list[OpportunityItem] = []
        sources: list[SourceItem] = []
        for key, notes in answers.items():
            task = tasks[key]
            if task.kind == "notes":
                continue
            item_type = OpportunityItem if task.kind == "opportunities" else SourceItem
            for i, chunk in enumerate(_chunks(notes), 1):
                try:
                    rows = self.llm.generate_json(_structure_prompt(task, chunk), item_type, tier="fast")
                except LLMError as exc:
                    log.error("task %s part %d: could not structure answer: %s", key, i, exc)
                    continue
                (opportunities if task.kind == "opportunities" else sources).extend(rows)
                self.sleep(self.settings.research_delay_seconds / 2)
        return opportunities, sources

    # -- step 3: never trust LLM URLs -----------------------------------------------------------------
    def verify(self, opportunities, sources) -> dict[str, UrlCheck]:
        pairs = [(o.url, f"{o.title} {o.organization}") for o in opportunities if o.url.startswith("http")]
        pairs += [(s.url, s.name) for s in sources if s.url.startswith("http")]
        return asyncio.run(check_urls(pairs, transport=self.url_transport))

    # -- step 4: store -----------------------------------------------------------------------------------
    def store(self, opportunities, sources, checks: dict[str, UrlCheck]) -> dict[str, int]:
        stats = {"opportunities_new": 0, "sources_new": 0, "dropped_dead": 0, "dropped_mismatch": 0,
                 "dropped_generic": 0, "dropped_duplicate": 0}
        before = len(opportunities)
        opportunities = [o for o in opportunities if not is_generic_url(o.url)]
        stats["dropped_generic"] = before - len(opportunities)
        before = len(opportunities)
        opportunities = dedupe_opportunities(opportunities)
        stats["dropped_duplicate"] = before - len(opportunities)
        kept_sources: list[dict] = []
        with db.session(self.settings.db_path) as conn:
            for o in opportunities:
                chk = checks.get(o.url)
                if not chk or chk.verdict == "dead":
                    stats["dropped_dead"] += 1
                    continue
                if chk.title_match is not None and chk.title_match < 0.25:
                    stats["dropped_mismatch"] += 1   # page exists but doesn't mention the program: likely hallucinated
                    continue
                if db.upsert_opportunity(
                    conn, category=o.category, title=o.title, direct_url=chk.final_url or o.url,
                    organization=o.organization, location=o.location, deadline=o.deadline, funding=o.funding,
                    moi_accepted=o.moi_accepted, gre_required=o.gre_required, notes=o.notes,
                    source="research:" + self.llm.name, verification=chk.verdict,
                ):
                    stats["opportunities_new"] += 1
            for s in sources:
                chk = checks.get(s.url)
                if not chk or chk.verdict == "dead":
                    stats["dropped_dead"] += 1
                    continue
                # Risky channels stay disabled until the user opts in (X/Twikit, Telethon, LinkedIn).
                enabled = s.type not in ("x_account",) and s.access_method != "login_required"
                if db.upsert_source(
                    conn, name=s.name, type=s.type, url=chk.final_url or s.url, origin="research", region=s.region,
                    category=s.category, access_method=s.access_method, scraping_notes=s.scraping_notes,
                    language=s.language, quality=s.quality, verification=chk.verdict, enabled=enabled,
                ):
                    stats["sources_new"] += 1
                kept_sources.append({**s.model_dump(), "verification": chk.verdict, "enabled": enabled})
            conn.execute("INSERT INTO research_runs(run_dir, summary) VALUES (?, ?)", (str(self.run_dir), str(stats)))
        out = ROOT / "config" / "sources_discovered.yaml"
        out.write_text(yaml.safe_dump({"generated": dt.datetime.now().isoformat(timespec="seconds"),
                                       "sources": kept_sources}, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return stats

    def run(self, only: set[str] | None = None, force: bool = False, dry_run: bool = False) -> dict[str, int]:
        answers = self.research(only, force)
        if dry_run:
            return {"answers_saved": len(answers)}
        opportunities, sources = self.structure(answers)
        checks = self.verify(opportunities, sources)
        return self.store(opportunities, sources, checks)
