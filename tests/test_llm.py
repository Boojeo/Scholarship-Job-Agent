import pytest
from pydantic import BaseModel

from src.llm.base import LLM, LLMError, LLMResponse, extract_json
from src.llm.gemini import GeminiLLM


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n[{"a": 1}]\n```') == [{"a": 1}]
    assert extract_json('Sure! Here you go: [1, 2, 3] hope it helps') == [1, 2, 3]
    with pytest.raises(ValueError):
        extract_json("no json here")


class Item(BaseModel):
    name: str


class Scripted(LLM):
    name = "scripted"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def generate(self, prompt, **kw):
        self.calls += 1
        return LLMResponse(self.outputs.pop(0), "scripted", "m")


def test_generate_json_repairs_once():
    llm = Scripted(["not json", '[{"name": "x"}]'])
    assert llm.generate_json("p", Item) == [Item(name="x")]
    assert llm.calls == 2


def test_generate_json_gives_up():
    with pytest.raises(LLMError):
        Scripted(["bad", "still bad"]).generate_json("p", Item)


class FakeResp:
    def __init__(self, text):
        self.text, self.candidates = text, []


def _client_error(code, msg="boom"):
    from google.genai import errors
    return errors.ClientError(code, {"error": {"message": msg, "status": "X"}})


def make_gemini(behaviours, keys=("k1", "k2")):
    used = []

    class Models:
        def __init__(self, key):
            self.key = key

        def generate_content(self, model, contents, config):
            used.append(self.key)
            action = behaviours[self.key].pop(0)
            if isinstance(action, Exception):
                raise action
            return FakeResp(action)

    class Client:
        def __init__(self, key):
            self.models = Models(key)

    sleeps = []
    llm = GeminiLLM(list(keys), {"fast": "m", "smart": "m", "research": "m"},
                    client_factory=Client, sleep=sleeps.append)
    return llm, used, sleeps


def test_gemini_rotates_key_on_quota():
    llm, used, _ = make_gemini({"k1": [_client_error(429)], "k2": ["hello"]})
    assert llm.generate("hi").text == "hello"
    assert used == ["k1", "k2"]


def test_gemini_waits_when_every_key_is_exhausted():
    llm, used, sleeps = make_gemini({"k1": [_client_error(429), "ok"], "k2": [_client_error(429)]})
    assert llm.generate("hi").text == "ok"
    assert sleeps  # waited once all keys were rate limited


def test_gemini_drops_rejected_key():
    llm, used, _ = make_gemini({"k1": [_client_error(400, "API key not valid")], "k2": ["fine"]})
    assert llm.generate("hi").text == "fine"
    assert llm._keys == ["k2"]


def test_gemini_unknown_model_message():
    llm, *_ = make_gemini({"k1": [_client_error(404, "not found")], "k2": []})
    with pytest.raises(LLMError, match="models"):
        llm.generate("hi")


def test_gemini_requires_key():
    with pytest.raises(LLMError):
        GeminiLLM([], {"fast": "m", "smart": "m", "research": "m"})


def test_probe_reports_api_error_text():
    llm, _, _ = make_gemini({"k1": [_client_error(404, "model is no longer available to new users")], "k2": []})
    out = llm.probe("old-model", search=False)
    assert out.startswith("404") and "no longer available" in out


def test_404_message_keeps_google_error():
    llm, *_ = make_gemini({"k1": [_client_error(404, "tool not supported")], "k2": []})
    with pytest.raises(LLMError, match="tool not supported"):
        llm.generate("hi")


# ---- Claude Code (Pro plan) provider -----------------------------------------------------------
import json as _json  # noqa: E402
import subprocess  # noqa: E402

from src.llm.claude_code import ClaudeCodeLLM  # noqa: E402


def _cc(outputs):
    calls = []

    def runner(cmd, **kw):
        calls.append((cmd, kw["input"]))
        code, payload = outputs.pop(0)
        return subprocess.CompletedProcess(cmd, code, stdout=_json.dumps(payload), stderr="")
    llm = ClaudeCodeLLM({"fast": "haiku", "smart": "sonnet", "research": "sonnet"}, executable="claude",
                        runner=runner, sleep=lambda s: None)
    return llm, calls


def test_claude_code_sends_prompt_on_stdin_with_tools_off():
    llm, calls = _cc([(0, {"is_error": False, "result": "hello"})])
    assert llm.generate("hi", tier="smart").text == "hello"
    cmd, stdin = calls[0]
    assert stdin == "hi" and cmd[cmd.index("--tools") + 1] == "" and cmd[cmd.index("--model") + 1] == "sonnet"


def test_claude_code_usage_limit_is_clear():
    llm, _ = _cc([(1, {"is_error": True, "result": "Claude AI usage limit reached|1793500000"})])
    with pytest.raises(LLMError, match="usage limit"):
        llm.generate("hi")


def test_claude_code_retries_transient_failure():
    llm, calls = _cc([(1, {"is_error": True, "result": "overloaded"}), (0, {"result": "[1]"})])
    assert llm.generate_json("p", int) == [1] and len(calls) == 2
