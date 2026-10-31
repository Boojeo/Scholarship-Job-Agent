import httpx
import yaml

from src.llm.base import LLM, LLMResponse, extract_json
from src.research import bootstrap as bs
from src.research.prompt import build_tasks
from src.settings import ROOT, Settings


def test_prompt_is_split_into_tasks():
    tasks = build_tasks(ROOT / "docs" / "gemini_research_prompt.md")
    assert [t.key for t in tasks] == ["A", "B", "C", "D1", "D2", "D3", "D4", "D5", "D6", "E"]
    assert all("30 October 2026" in t.prompt for t in tasks)
    assert "+966" not in tasks[0].prompt and "@gmail" not in tasks[0].prompt  # no contact details leak


class FakeLLM(LLM):
    name = "fake"

    def generate(self, prompt, *, search=False, **kw):
        if search:
            return LLMResponse(f"research notes for: {prompt[:30]}", "fake", "m")
        if "'CATEGORY_1_SCHOLARSHIP'" in prompt:
            rows = [
                {"category": "CATEGORY_1_SCHOLARSHIP", "title": "Real MSc AI Program", "organization": "Uni",
                 "url": "https://good.example/msc", "moi_accepted": "yes"},
                {"category": "CATEGORY_1_SCHOLARSHIP", "title": "Invented Scholarship", "organization": "Nowhere",
                 "url": "https://dead.example/x"},
                {"category": "CATEGORY_1_SCHOLARSHIP", "title": "Quantum Basket Weaving Fellowship",
                 "organization": "Unrelated", "url": "https://other.example/page"},
            ]
        elif "name, type" in prompt:
            rows = [{"name": "Good Portal", "type": "portal", "url": "https://good.example/portal", "quality": 4},
                    {"name": "X feed", "type": "x_account", "url": "https://good.example/x"}]
        else:
            rows = []
        import json
        return LLMResponse(json.dumps(rows), "fake", "m")


def handler(request: httpx.Request) -> httpx.Response:
    host = request.url.host
    if host == "dead.example":
        return httpx.Response(404)
    if host == "other.example":
        return httpx.Response(200, text="<html>cats and dogs</html>", headers={"content-type": "text/html"})
    return httpx.Response(200, text="<html>Real MSc AI Program at Uni. Good Portal</html>",
                          headers={"content-type": "text/html"})


def test_pipeline_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "ROOT", tmp_path)
    (tmp_path / "config").mkdir()
    settings = Settings(db_path=tmp_path / "t.sqlite3", data_dir=tmp_path, research_delay_seconds=0)
    run = bs.ResearchBootstrap(FakeLLM(), settings, sleep=lambda s: None,
                               url_transport=httpx.MockTransport(handler), run_dir=tmp_path / "run",
                               mode="grounded")
    stats = run.run()
    assert stats["opportunities_new"] == 1          # only the verified, matching one survives
    assert stats["dropped_dead"] >= 1               # 404 link rejected
    assert stats["dropped_mismatch"] == 1           # live page that doesn't mention the program rejected
    assert stats["sources_new"] == 2
    assert (tmp_path / "run" / "A.md").exists()      # raw answers kept for resume

    out = yaml.safe_load((tmp_path / "config" / "sources_discovered.yaml").read_text())
    by_name = {s["name"]: s for s in out["sources"]}
    assert by_name["X feed"]["enabled"] is False     # risky channels stay opt-in
    assert by_name["Good Portal"]["enabled"] is True


def test_resume_reuses_saved_answers(tmp_path):
    settings = Settings(db_path=tmp_path / "t.sqlite3", data_dir=tmp_path, research_delay_seconds=0)

    class Boom(LLM):
        name = "boom"

        def generate(self, *a, **k):
            raise AssertionError("must not call the model when an answer is saved")

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "A.md").write_text("saved")
    run = bs.ResearchBootstrap(Boom(), settings, run_dir=run_dir, sleep=lambda s: None)
    assert run.research(only={"A"}) == {"A": "saved"}


# ---- free web route ---------------------------------------------------------------------------
from src.research import web  # noqa: E402


def test_html_to_text_keeps_links_and_drops_scripts():
    html = ("<html><script>evil()</script><body><h1>MSc AI Scholarship</h1>"
            "<p>" + "Fully funded for international students. " * 20 + "</p>"
            "<a href='/apply'>Apply now online</a></body></html>")
    text = web.html_to_text(html, "https://u.edu/page")
    assert "evil" not in text and "MSc AI Scholarship" in text
    assert "Apply now online -> https://u.edu/apply" in text


def test_collect_hits_dedupes_and_skips_social():
    def fake_search(q, n):
        return [web.SearchHit("t", "https://a.edu/x?utm_source=z", "s"), web.SearchHit("t", "https://A.edu/x/", "s"),
                web.SearchHit("t", "https://x.com/someone", "tweet")]
    hits = web.collect_hits(["q1", "q2"], fake_search, sleep=lambda s: None)
    assert [h.url for h in hits] == ["https://a.edu/x?utm_source=z", "https://x.com/someone"]
    assert web.is_fetchable("https://a.edu/x") and not web.is_fetchable("https://x.com/someone")


def test_web_mode_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "ROOT", tmp_path)
    (tmp_path / "config").mkdir()
    page = "<html><body><h1>Real MSc AI Program at Uni</h1><p>" + "Funded places for applicants. " * 30 + "</p></body></html>"

    def search(q, n):
        return [web.SearchHit("Real MSc AI Program", "https://good.example/msc", "snippet")]

    def pages(request):
        return httpx.Response(200, text=page, headers={"content-type": "text/html"})

    class WebLLM(FakeLLM):
        def generate(self, prompt, **kw):
            assert "### PAGE https://good.example/msc" in prompt or "name, type" in prompt or "CATEGORY" in prompt
            return super().generate(prompt, **kw)

    settings = Settings(db_path=tmp_path / "t.sqlite3", data_dir=tmp_path, research_delay_seconds=0)
    run = bs.ResearchBootstrap(WebLLM(), settings, sleep=lambda s: None, url_transport=httpx.MockTransport(pages),
                               run_dir=tmp_path / "run", mode="web", search_fn=search)
    answers = run.research(only={"A"})
    assert "### PAGE https://good.example/msc" in answers["A"]
    assert not (tmp_path / "run" / "E.md").exists()


def test_chunks_split_on_page_markers():
    notes = "".join(f"### PAGE https://x/{i}\n" + "a" * 20_000 + "\n" for i in range(5))
    chunks = bs._chunks(notes, max_chars=45_000)
    assert len(chunks) >= 2 and all(len(c) < 90_000 for c in chunks)
    assert "".join(chunks) == notes


def test_gemini_switches_to_suggested_model():
    from tests.test_llm import make_gemini, _client_error
    msg = "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest"
    llm, used, _ = make_gemini({"k1": [_client_error(404, msg), "hello"], "k2": []})
    assert llm.generate("hi").text == "hello"
    assert llm._models["fast"] == "gemini-3.8-flash"


# ---- result quality filters ------------------------------------------------------------------
from src.research.schemas import OpportunityItem  # noqa: E402


def _opp(title, org, url, deadline=""):
    return OpportunityItem(category="CATEGORY_1_SCHOLARSHIP", title=title, organization=org, url=url, deadline=deadline)


def test_generic_urls_are_rejected():
    assert bs.is_generic_url("https://research.ibm.com/")
    assert bs.is_generic_url("https://openai.com/careers/")
    assert bs.is_generic_url("https://www.scholarshipsads.com/search/degree/masters")
    assert not bs.is_generic_url("https://www.imperial.ac.uk/study/fees-and-funding/scholarships-search/sparck-ai.php")
    assert not bs.is_generic_url("https://scholarpositions.com/mbzuai-scholarship-2027/")


def test_aggregator_copies_collapse_and_official_site_wins():
    org = "Mohamed bin Zayed University of Artificial Intelligence"
    items = [
        _opp("MBZUAI Scholarship 2027: Fully Funded", org, "https://blog.example/mbzuai", "December 15, 2026"),
        _opp("MBZUAI Graduate Funding 2027", org + " (MBZUAI)", "https://mbzuai.ac.ae/study/funding", "December 15, 2026 at 5:00 p.m. GST"),
        _opp("Spärck AI Scholarship", "Imperial College London", "https://imperial.ac.uk/x/sparck", ""),
    ]
    out = bs.dedupe_opportunities(items)
    assert [o.url for o in out] == ["https://mbzuai.ac.ae/study/funding", "https://imperial.ac.uk/x/sparck"]
