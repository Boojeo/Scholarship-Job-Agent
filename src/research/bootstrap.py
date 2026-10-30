"""Automated research bootstrap.

Runs the research prompt through a web-grounded LLM (Gemini), turns the answers into structured rows,
verifies every URL over HTTP, and stores what survives in SQLite plus config/sources_discovered.yaml.
Raw answers are saved so an interrupted run can resume without spending quota again.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import time
from pathlib import Path
from typing import Callable

import yaml

from src.database import db
from src.llm.base import LLM, LLMError
from src.research.prompt import ResearchTask, build_tasks
from src.research.schemas import OpportunityItem, SourceItem
from src.research.verify import UrlCheck, check_urls
from src.settings import ROOT, Settings

log = logging.getLogger(__name__)
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
    return ("Convert the research notes below into a JSON array. Each element has these fields: "
            f"{fields}.\nRules: include only items that have a real http(s) URL in the notes; copy facts "
            "exactly, use \"\" or \"unknown\" when the notes do not say; add nothing that is not in the notes; "
            "drop items marked UNVERIFIED or expired.\n\nNOTES:\n" + notes)


class ResearchBootstrap:
    def __init__(self, llm: LLM, settings: Settings, *, run_dir: Path | None = None,
                 prompt_file: Path = PROMPT_FILE, sleep: Callable[[float], None] = time.sleep,
                 url_transport=None):
        self.llm = llm
        self.settings = settings
        self.prompt_file = prompt_file
        self.sleep = sleep
        self.url_transport = url_transport
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
            log.info("task %s: researching (web-grounded)...", task.key)
            try:
                resp = self.llm.generate(task.prompt, system=SYSTEM, tier="research", search=True,
                                         max_tokens=32768, temperature=0.2)
            except LLMError as exc:
                log.error("task %s failed: %s", task.key, exc)
                continue
            raw.write_text(resp.text, encoding="utf-8")
            answers[task.key] = resp.text
            self.sleep(self.settings.research_delay_seconds)
        return answers

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
            try:
                rows = self.llm.generate_json(_structure_prompt(task, notes), item_type, tier="fast")
            except LLMError as exc:
                log.error("task %s: could not structure answer: %s", key, exc)
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
        stats = {"opportunities_new": 0, "sources_new": 0, "dropped_dead": 0, "dropped_mismatch": 0}
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
