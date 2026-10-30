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
                               url_transport=httpx.MockTransport(handler), run_dir=tmp_path / "run")
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
