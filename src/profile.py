"""Candidate profile loaded once from config/candidate_profile.yaml, plus the short text every prompt uses."""
from __future__ import annotations

from functools import lru_cache

import yaml

from src.settings import ROOT

PROFILE_FILE = ROOT / "config" / "candidate_profile.yaml"


@lru_cache(maxsize=1)
def load_profile() -> dict:
    return yaml.safe_load(PROFILE_FILE.read_text(encoding="utf-8"))


def profile_brief() -> str:
    c = load_profile()["candidate"]
    e = c["education"]
    return (
        f"Candidate: {c['name']}, {c['nationality']} national, resident in {' and '.join(c['residencies'])}. "
        f"{e['degree']} at {e['university']}, GPA {e['gpa']}, graduating {e['expected_graduation']}. "
        "Has an English Medium-of-Instruction letter, no IELTS/TOEFL yet, no GRE/GMAT. "
        "Co-author of an LLM long-context paper (arXiv 2610.04047, under review at ICML); KAUST Academy summer program 2026. "
        "Wants: (1) fully funded MS or direct PhD in AI/ML/CS starting 2027, (2) AI/CS internships, co-op or "
        "part-time roles, (3) entry-level AI/ML/data/software jobs from mid-2027 (or remote/part-time now)."
    )
