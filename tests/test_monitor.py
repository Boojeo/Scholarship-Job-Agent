import json

import httpx

from src.database import db
from src.llm.base import LLM, LLMResponse
from src.monitor import readers
from src.monitor.readers import RawItem, Source
from src.monitor.run import Monitor
from src.monitor.screen import keyword_filter
from src.settings import Settings

TG_HTML = """<div class="tgme_widget_message" data-post="chan/41"><div class="tgme_widget_message_text">
Fully funded MSc Artificial Intelligence scholarship 2027 at Uni X. Apply:
<a href="https://uni.example/msc-ai">link</a> <a href="https://t.me/other">tg</a></div>
<time datetime="2026-10-30T10:00:00+00:00"></time></div>
<div class="tgme_widget_message" data-post="chan/42"><div class="tgme_widget_message_text">Join our VIP group</div></div>"""

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>PhD Scholarship in Machine Learning 2027</title><link>https://site.example/phd-ml</link>
<description>&lt;p&gt;Fully funded PhD for international students.&lt;/p&gt;</description></item></channel></rss>"""


def src(kind, url="https://x.example/feed/", cat="CATEGORY_1_SCHOLARSHIP"):
    return Source("S", kind, url, cat)


def test_telegram_parser_takes_external_link():
    items = readers.parse_telegram(TG_HTML, src("telegram"))
    assert items[0].key == "tg:chan/41" and items[0].url == "https://uni.example/msc-ai"
    assert items[1].url == "https://t.me/chan/42"


def test_rss_parser_strips_html():
    item = readers.parse_rss(RSS, src("rss"))[0]
    assert item.url == "https://site.example/phd-ml" and "<p>" not in item.text


def test_json_simplify_keeps_recent_tech_roles():
    import datetime as dt
    now = dt.datetime(2026, 10, 31, tzinfo=dt.timezone.utc)
    rows = [{"id": 1, "title": "Machine Learning Intern", "company_name": "A", "url": "https://a/1",
             "date_posted": now.timestamp() - 3600, "locations": ["Remote"]},
            {"id": 2, "title": "Marketing Intern", "company_name": "B", "url": "https://b/2",
             "date_posted": now.timestamp()},
            {"id": 3, "title": "Software Engineer Intern", "company_name": "C", "url": "https://c/3",
             "date_posted": now.timestamp() - 10 * 86400}]
    out = readers.parse_json(json.dumps(rows).encode(), src("json_api", "https://raw.githubusercontent.com/x"), now)
    assert [i.url for i in out] == ["https://a/1"]


def test_keyword_filter():
    ok = RawItem("S", "CATEGORY_1_SCHOLARSHIP", "k", "Fully funded MSc AI scholarship", "", "https://u")
    senior = RawItem("S", "CATEGORY_3_FULLTIME", "k", "Senior ML Engineer, 7+ years", "", "https://u")
    spam = RawItem("S", "CATEGORY_1_SCHOLARSHIP", "k", "Join our VIP group", "", "https://u")
    assert keyword_filter(ok) and not keyword_filter(senior) and not keyword_filter(spam)


class ScreenLLM(LLM):
    name = "fake"

    def __init__(self):
        self.calls = 0

    def generate(self, prompt, **kw):
        self.calls += 1
        n = prompt.count("\n[")
        rows = [{"index": i, "keep": True, "category": "CATEGORY_1_SCHOLARSHIP", "title": f"Item {i}",
                 "organization": "Uni", "match_score": 80, "why_it_matches": "GPA",
                 "missing_documents": ["IELTS"]} for i in range(n)]
        return LLMResponse(json.dumps(rows), "fake", "m")


def test_monitor_end_to_end_and_dedupes_next_run(tmp_path):
    settings = Settings(db_path=tmp_path / "db.sqlite3", data_dir=tmp_path)
    with db.session(settings.db_path) as conn:
        db.upsert_source(conn, name="Chan", type="telegram", url="https://t.me/s/chan",
                         category="CATEGORY_1_SCHOLARSHIP")
        db.upsert_source(conn, name="Feed", type="rss", url="https://site.example/feed/",
                         category="CATEGORY_1_SCHOLARSHIP")

    def handler(req: httpx.Request):
        if req.url.host == "t.me":
            return httpx.Response(200, text=TG_HTML)
        return httpx.Response(200, content=RSS, headers={"content-type": "application/rss+xml"})

    llm = ScreenLLM()
    mon = Monitor(llm, settings, transport=httpx.MockTransport(handler), fallback=False)
    rep = mon.run()
    assert rep.items_new == 3 and rep.after_keywords == 2 and rep.stored_new == 2
    with db.session(settings.db_path) as conn:
        row = conn.execute("SELECT * FROM opportunities WHERE direct_url = 'https://uni.example/msc-ai'").fetchone()
        assert row["match_score"] == 80 and json.loads(row["missing_documents"]) == ["IELTS"]
    calls = llm.calls
    rep2 = mon.run()
    assert rep2.items_new == 0 and llm.calls == calls      # nothing re-sent to the model


def test_fallback_search_runs_for_thin_category(tmp_path):
    settings = Settings(db_path=tmp_path / "db.sqlite3", data_dir=tmp_path)
    from src.research.web import SearchHit

    def search(q, n):
        return [SearchHit("Fully funded MSc AI scholarship 2027", f"https://s.example/{abs(hash(q))}", "funded")]

    rep = Monitor(ScreenLLM(), settings, transport=httpx.MockTransport(lambda r: httpx.Response(404)),
                  search_fn=search).run("CATEGORY_1_SCHOLARSHIP")
    assert rep.fallback_used == ["scholarship"] and rep.stored_new >= 1
