"""Split docs/gemini_research_prompt.md into one self-contained prompt per research task."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SOURCE_GROUPS = [
    "1. Scholarship / PhD aggregators and official university portals",
    "2. Job boards and company career pages for Saudi/UAE/GCC and global remote work",
    "3. Public Telegram channels (confirm https://t.me/s/<handle> shows recent posts)",
    "4. X (Twitter) accounts and English/Arabic search queries",
    "5. YouTube channels that regularly post funded scholarships or AI internships",
    "6. Newsletters, RSS feeds and public APIs",
]


@dataclass
class ResearchTask:
    key: str          # A, B, C, D1..D6, E
    prompt: str
    kind: str         # opportunities | sources | notes
    category: str | None = None


def build_tasks(prompt_file: Path) -> list[ResearchTask]:
    text = prompt_file.read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1]
    header = body.split("## Tasks", 1)[0].strip()
    rules = body.split("## Rules", 1)[1].strip() if "## Rules" in body else ""
    sections = {m.group(1): m.group(0) for m in re.finditer(
        r"### Task ([A-E]):.*?(?=\n### Task |\n## Output format)", body, re.DOTALL)}
    if set(sections) != set("ABCDE"):
        raise ValueError(f"research prompt is missing tasks; found {sorted(sections)}")

    fmt = ("\n\nOutput for this call: a Markdown table with one row per item and the URL you opened in its own "
           "column, then a short list of anything you could not verify. Do not write any other sections.")
    tasks = [
        ResearchTask("A", f"{header}\n\n{sections['A']}{fmt}\n\n## Rules\n{rules}", "opportunities", "CATEGORY_1_SCHOLARSHIP"),
        ResearchTask("B", f"{header}\n\n{sections['B']}{fmt}\n\n## Rules\n{rules}", "opportunities", "CATEGORY_2_COOP_PARTTIME"),
        ResearchTask("C", f"{header}\n\n{sections['C']}{fmt}\n\n## Rules\n{rules}", "opportunities", "CATEGORY_3_FULLTIME"),
    ]
    for i, group in enumerate(SOURCE_GROUPS, 1):
        focus = (f"\n\nFor this call cover ONLY source group {group}. Return at least 15 verified sources of this "
                 "group as a Markdown table with every field of Task D (name, type, url, region, category, "
                 "update_frequency, access_method, scraping_notes, language, quality).")
        tasks.append(ResearchTask(f"D{i}", f"{header}\n\n{sections['D']}{focus}\n\n## Rules\n{rules}", "sources"))
    tasks.append(ResearchTask("E", f"{header}\n\n{sections['E']}\n\nOutput: a bullet list only.\n\n## Rules\n{rules}", "notes"))
    return tasks
