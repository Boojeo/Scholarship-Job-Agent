"""Tailor CV + letter + email to one opportunity, then check every claim against the master CV."""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
from dataclasses import dataclass, field

from pydantic import BaseModel

from src.llm.base import LLM, LLMError
from src.profile import profile_brief
from src.research import web
from src.settings import Settings

log = logging.getLogger(__name__)

RULES = """Hard rules:
- Use ONLY facts from the MASTER CV. Never add skills, tools, employers, projects, publications, dates, grades or
  awards that are not in it. You may reorder, shorten, rephrase, choose what to emphasise, and reuse the posting's
  keywords ONLY where the master CV supports them.
- Keep {{EMAIL}} and {{PHONE}} placeholders exactly as they are.
- The degree is not finished: the graduation date is "expected July 2027". "First Class Honors standing" may be used as written.
- Name: Abdallah Ahmed Mohamud (passport name). The paper lists him as "Abdallah Ahmed"; keep the citation as published.
- English is the language of instruction of the degree (MOI letter available); IELTS has not been taken yet."""


class Answer(BaseModel):
    question: str
    answer: str


class Package(BaseModel):
    cv_markdown: str
    letter_title: str
    letter_markdown: str
    email_subject: str
    email_body: str
    portal_answers: list[Answer] = []
    required_documents: list[str] = []


class FabricationCheck(BaseModel):
    unsupported_claims: list[str] = []


@dataclass
class TailorResult:
    package: Package
    unsupported: list[str] = field(default_factory=list)
    posting_text: str = ""


def load_master(settings: Settings, category: str) -> str:
    name = "master_cv_research.md" if category == "CATEGORY_1_SCHOLARSHIP" else "master_cv_industry.md"
    return (settings.vault_dir / name).read_text(encoding="utf-8")


def fetch_posting(url: str, fallback: str) -> str:
    try:
        pages = asyncio.run(web.fetch_pages([url], max_chars=12000))
    except Exception as exc:  # network trouble must not stop tailoring
        log.warning("could not fetch posting %s: %s", url, exc)
        pages = {}
    return pages.get(url) or fallback


def build_prompt(opp: dict, master: str, posting: str, feedback: str = "") -> str:
    scholarship = opp["category"] == "CATEGORY_1_SCHOLARSHIP"
    letter = ("a Statement of Purpose (500-800 words) for this program, specific to its research areas and labs "
              "named in the posting" if scholarship else
              "a one-page cover letter (250-350 words) for this role")
    email = ("a short cold email to a professor/lab at this university (150-200 words) asking about MS/PhD "
             "supervision, mentioning the GPA, the Periscope paper and the MOI letter" if scholarship else
             "a short recruiter / hiring-manager message (120-160 words)")
    extra = f"\nUSER FEEDBACK ON THE PREVIOUS VERSION (apply it): {feedback}\n" if feedback else ""
    return f"""Today is {dt.date.today()}. {profile_brief()}

Write an application package for the opportunity below. Return JSON with:
cv_markdown (a 1-2 page CV in Markdown, '# Name' then '## Section' headings and '- ' bullets, tailored to the
posting), letter_title, letter_markdown ({letter}), email_subject, email_body ({email}), portal_answers
(answers to the questions application forms usually ask for this kind of opportunity, e.g. motivation, why this
program/company, research interests, career goals, availability, visa/residency status - each 60-150 words,
only from facts in the master CV and profile), required_documents (documents the posting asks for).

{RULES}
{extra}
OPPORTUNITY: {opp['title']} | {opp.get('organization') or ''} | {opp.get('location') or ''} | deadline: {opp.get('deadline') or 'unknown'}
POSTING TEXT:
{posting[:12000]}

MASTER CV:
{master}"""


def check_prompt(master: str, pkg: Package) -> str:
    return f"""Compare the GENERATED documents with the MASTER CV and profile. List every claim in the generated
documents that is not supported by the master CV or profile (invented skills, tools, employers, projects,
numbers, dates, awards, publications, or saying the degree is finished). Wording changes and emphasis are fine.
Return JSON: {{"unsupported_claims": [..]}} with an empty list if everything is supported.

PROFILE: {profile_brief()}

MASTER CV:
{master}

GENERATED CV:
{pkg.cv_markdown}

GENERATED LETTER:
{pkg.letter_markdown}

GENERATED EMAIL:
{pkg.email_body}

GENERATED ANSWERS:
{chr(10).join(a.answer for a in pkg.portal_answers)}"""


def tailor(llm: LLM, settings: Settings, opp: dict, feedback: str = "") -> TailorResult:
    master = load_master(settings, opp["category"])
    posting = fetch_posting(opp["direct_url"], opp.get("notes") or opp["title"])
    pkg: Package | None = None
    unsupported: list[str] = []
    for attempt in range(2):
        note = feedback if attempt == 0 else (
            f"{feedback}\nThe previous draft contained unsupported claims; remove them: {unsupported}")
        pkg = llm.generate_json(build_prompt(opp, master, posting, note), Package, tier="smart", many=False,
                                max_tokens=16384)
        try:
            unsupported = llm.generate_json(check_prompt(master, pkg), FabricationCheck, tier="fast",
                                            many=False).unsupported_claims
        except LLMError as exc:
            log.warning("fabrication check failed: %s", exc)
            unsupported = ["fabrication check could not run - review manually"]
        if not unsupported:
            break
    return TailorResult(package=pkg, unsupported=unsupported, posting_text=posting)


def fill_contacts(text: str, settings: Settings) -> str:
    return text.replace("{{EMAIL}}", settings.candidate_email or "").replace(
        "{{PHONE}}", settings.candidate_phone or "")
