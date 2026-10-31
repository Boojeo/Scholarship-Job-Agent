"""Turn raw posts into scored opportunities: free keyword filter first, then one Gemini call per batch."""
from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Literal

from pydantic import BaseModel

from src.llm.base import LLM, LLMError
from src.monitor.readers import RawItem
from src.profile import profile_brief

log = logging.getLogger(__name__)
BATCH = 20

KEEP = {
    "CATEGORY_1_SCHOLARSHIP": r"scholarship|fellowship|funded|master|msc|m\.sc|phd|ph\.d|doctoral|graduate|stipend|"
                              r"منح|منحة|ماجستير|دكتوراه|ممولة",
    "CATEGORY_2_COOP_PARTTIME": r"intern|co-?op|trainee|training|summer|part[- ]time|student|graduate program|"
                                r"research assistant|تدريب|تعاوني|تمهير|متدرب|طلاب|دوام جزئي",
    "CATEGORY_3_FULLTIME": r"engineer|developer|scientist|data|software|machine learning|\bai\b|\bml\b|python|"
                           r"analyst|graduate|junior|entry|حديثي التخرج|مطور|مهندس|برمج|بيانات|ذكاء|تقني|حاسب",
}
DROP = re.compile(r"\bsenior\b|\blead\b|\bprincipal\b|\bstaff engineer\b|\b(?:[5-9]|1\d)\+? ?years\b|"
                  r"undergraduate (?:only|scholarship)|bachelor'?s scholarship|high school|"
                  r"خبرة لا تقل عن (?:5|خمس)", re.I)
TECH_OR_ACADEMIC = re.compile(r"comput|ai\b|artificial|machine|data|software|engineer|science|stem|any field|"
                              r"all fields|all subjects|technology|research|حاسب|ذكاء|تقني|برمج|بيانات|جميع التخصصات|"
                              r"scholarship|منحة|منح", re.I)


def keyword_filter(item: RawItem) -> bool:
    blob = f"{item.title} {item.text}"
    if DROP.search(blob):
        return False
    if not re.search(KEEP.get(item.category_hint, "."), blob, re.I):
        return False
    return bool(TECH_OR_ACADEMIC.search(blob))


class Screened(BaseModel):
    index: int
    keep: bool
    category: Literal["CATEGORY_1_SCHOLARSHIP", "CATEGORY_2_COOP_PARTTIME", "CATEGORY_3_FULLTIME"]
    title: str = ""
    organization: str = ""
    location: str = ""
    deadline: str = ""
    funding: str = ""
    moi_accepted: Literal["yes", "no", "unknown"] = "unknown"
    gre_required: Literal["yes", "no", "unknown"] = "unknown"
    ielts_required_upfront: bool = False
    match_score: int = 0
    why_it_matches: str = ""
    official_url: str = ""
    missing_documents: list[str] = []


SYSTEM = ("You screen scholarship, internship and job posts for one candidate. You are strict: you never invent "
          "facts, deadlines or links that are not in the post.")


def screen_prompt(batch: list[RawItem]) -> str:
    today = dt.date.today().isoformat()
    posts = "\n\n".join(
        f"[{i}] SOURCE: {it.source} (usually {it.category_hint})\nTITLE: {it.title}\nLINK: {it.url}\n"
        f"OTHER LINKS: {', '.join(it.links) or '-'}\nTEXT: {it.text}" for i, it in enumerate(batch))
    return f"""Today is {today}. {profile_brief()}

For EVERY post below return one JSON object with: index, keep (true/false), category
(CATEGORY_1_SCHOLARSHIP = funded MS/PhD/scholarship; CATEGORY_2_COOP_PARTTIME = internship, co-op, training,
part-time, research internship; CATEGORY_3_FULLTIME = full-time or graduate job), title, organization, location,
deadline (as written, "" if none), funding, moi_accepted (yes/no/unknown: does it accept a Medium-of-Instruction
letter or waive IELTS/TOEFL?), gre_required (yes/no/unknown), ielts_required_upfront (true only if the post says
IELTS/TOEFL is mandatory with no waiver), match_score (0-100), why_it_matches (one short sentence naming the
concrete advantage: GPA 4.99, AI research paper, KSA/UAE residency, Somali/African/OIC eligibility...),
official_url (the official application/program link if it appears in the post, else ""), missing_documents
(documents the post requires that the candidate may not have, e.g. "IELTS", "GRE", "recommendation letters",
"research proposal").

Set keep=false when: the deadline has passed; it is not AI/CS/STEM-related and not open to all fields; it is only
for undergraduates, high-school students or a nationality that excludes Somali citizens; it needs 3+ years of
experience or a completed PhD; it is not funded (scholarships) or unpaid (jobs) with no clear benefit; it is spam,
a paid service, an advert or a course; it requires citizenship or work authorization the candidate does not
have (e.g. US citizens only, no visa sponsorship outside KSA/UAE) unless it is remote or a funded program that provides the visa. Score high for fully funded AI/CS master's or PhD, MOI accepted, no GRE,
AI/ML roles open to new graduates or remote. Score below 50 anything doubtful.

POSTS:
{posts}"""


def screen(llm: LLM, items: list[RawItem]) -> list[tuple[RawItem, Screened]]:
    kept: list[tuple[RawItem, Screened]] = []
    for start in range(0, len(items), BATCH):
        batch = items[start:start + BATCH]
        try:
            results = llm.generate_json(screen_prompt(batch), Screened, system=SYSTEM, tier="fast")
        except LLMError as exc:
            log.error("screening batch %d failed: %s", start // BATCH + 1, exc)
            continue
        for r in results:
            if 0 <= r.index < len(batch) and r.keep:
                kept.append((batch[r.index], r))
    return kept
