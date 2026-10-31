import json

from src.applicator import kit
from src.bot.digest import card, pending_for_digest
from src.database import db
from src.llm.base import LLM, LLMResponse
from src.settings import ROOT, Settings
from src.tailor import tailor as tl
from src.tailor.render import render_both

OPP = {"id": 1, "category": "CATEGORY_1_SCHOLARSHIP", "title": "MSc AI 2027", "organization": "Uni X",
       "location": "Germany", "deadline": "Dec 1, 2026", "direct_url": "https://uni.example/msc",
       "notes": "Fully funded MSc. Requires CV, motivation letter, transcript, IELTS.", "match_score": 88,
       "why_it_matches": "GPA"}


def test_render_pdf_and_docx(tmp_path):
    pdf, docx = render_both("# Name\n## Education\n- **B.Sc.** CS, GPA 4.99\nplain line", tmp_path / "cv")
    assert pdf.read_bytes()[:4] == b"%PDF" and docx.stat().st_size > 1000


class TailorLLM(LLM):
    name = "fake"

    def __init__(self, unsupported_first=False):
        self.unsupported_first = unsupported_first
        self.checks = 0

    def generate(self, prompt, **kw):
        if "unsupported_claims" in prompt:
            self.checks += 1
            bad = ["Claims PyTorch"] if self.unsupported_first and self.checks == 1 else []
            return LLMResponse(json.dumps({"unsupported_claims": bad}), "fake", "m")
        assert "MASTER CV" in prompt and "Periscope" in prompt
        return LLMResponse(json.dumps({
            "cv_markdown": "# Abdallah Mohamud\n{{EMAIL}} | {{PHONE}}\n## Education\n- B.Sc. CS, expected July 2027",
            "letter_title": "SOP", "letter_markdown": "# Statement of Purpose\nI want to study AI.",
            "email_subject": "MS inquiry", "email_body": "Dear Prof.,\nRegards, {{EMAIL}}",
            "portal_answers": [{"question": "Why us?", "answer": "Your NLP lab."}],
            "required_documents": ["CV", "Transcript", "IELTS certificate"]}), "fake", "m")


def test_tailor_retries_after_fabrication_and_builds_kit(tmp_path, monkeypatch):
    monkeypatch.setattr(tl, "fetch_posting", lambda url, fb: fb)
    vault = tmp_path / "vault"
    (vault / "attachments").mkdir(parents=True)
    (vault / "master_cv_research.md").write_text((ROOT / "vault" / "master_cv_research.md").read_text(encoding="utf-8"),
                                                 encoding="utf-8")
    (vault / "attachments" / "my_transcript.pdf").write_bytes(b"%PDF-1.4")
    settings = Settings(vault_dir=vault, kits_dir=tmp_path / "kits", candidate_email="me@x.com",
                        candidate_phone="+966")
    llm = TailorLLM(unsupported_first=True)
    result = tl.tailor(llm, settings, OPP)
    assert llm.checks == 2 and result.unsupported == []
    folder = kit.build_kit(settings, OPP, result)
    names = {p.name for p in folder.iterdir()}
    assert {"01_Tailored_CV.pdf", "01_Tailored_CV.docx", "02_Statement_of_Purpose.pdf", "03_Email.txt",
            "Transcript.pdf", "00_APPLICATION_INSTRUCTIONS.md"} <= names
    instructions = (folder / "00_APPLICATION_INSTRUCTIONS.md").read_text(encoding="utf-8")
    assert "IELTS certificate" in instructions and "Transcript\n" not in instructions.split("NOT in your vault")[1]
    assert "me@x.com" in (folder / "03_Email.txt").read_text(encoding="utf-8")


def test_digest_groups_and_card(tmp_path):
    conn = db.connect(":memory:")
    db.upsert_opportunity(conn, category="CATEGORY_1_SCHOLARSHIP", title="A <b>", direct_url="https://a/1")
    db.set_fields(conn, "https://a/1", match_score=90, missing_documents='["GRE"]')
    db.upsert_opportunity(conn, category="CATEGORY_3_FULLTIME", title="Low", direct_url="https://b/1")
    db.set_fields(conn, "https://b/1", match_score=20)
    groups = pending_for_digest(conn, 60)
    assert [o["title"] for o in groups["CATEGORY_1_SCHOLARSHIP"]] == ["A <b>"] and groups["CATEGORY_3_FULLTIME"] == []
    text = card(groups["CATEGORY_1_SCHOLARSHIP"][0])
    assert "A &lt;b&gt;" in text and "Missing: GRE" in text


def test_browser_field_values_cover_basics():
    from src.applicator.browser import field_values
    vals = field_values(Settings(candidate_email="me@x.com", candidate_phone="+966"))
    def pick(hint):
        return next(v for p, v in vals if p.search(hint))
    assert pick("firstName") == "Abdallah" and pick("email") == "me@x.com" and pick("gpa") == "4.99 / 5.00"


def test_db_migration_adds_columns(tmp_path):
    import sqlite3
    path = tmp_path / "old.sqlite3"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE opportunities (id INTEGER PRIMARY KEY, url_hash TEXT UNIQUE, category TEXT, "
                "title TEXT, direct_url TEXT, status TEXT DEFAULT 'new', match_score INTEGER)")
    old.commit()
    old.close()
    conn = db.connect(path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(opportunities)")}
    assert {"missing_documents", "ielts_upfront"} <= cols


def test_browser_uses_passport_name_parts():
    from src.applicator.browser import field_values
    vals = field_values(Settings(candidate_email="me@x.com"))
    pick = lambda h: next(v for p, v in vals if p.search(h))  # noqa: E731
    assert (pick("middleName"), pick("lastName"), pick("full_name")) == ("Ahmed", "Mohamud", "Abdallah Ahmed Mohamud")
