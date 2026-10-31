"""Claude through the Claude Code CLI (`claude -p`), using the Pro/Max plan you are logged into. No API key.

Each call starts `claude` in headless mode with all tools disabled, sends the prompt on stdin and reads the JSON
result. Usage counts toward your plan's limits; when a limit is hit the error says so and the run stops cleanly.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from typing import Callable

from pydantic import BaseModel

from .base import LLM, LLMError, LLMResponse, Tier

log = logging.getLogger(__name__)
JSON_SYSTEM = "You are a careful assistant inside an automation pipeline. Follow the output format exactly."


def find_claude(configured: str | None = None) -> str | None:
    """CLAUDE_CODE_PATH, then PATH, then the usual Windows/macOS/Linux install locations."""
    if configured and os.path.exists(configured):
        return configured
    found = shutil.which("claude")
    if found:
        return found
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".local", "bin", "claude.exe"),            # Windows native installer
        os.path.join(home, ".local", "bin", "claude"),                # macOS/Linux native installer
        os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd"),  # npm install -g on Windows
        os.path.join(home, ".claude", "local", "claude"),
    ]
    return next((c for c in candidates if c and os.path.exists(c)), None)


class ClaudeCodeLLM(LLM):
    name = "claude_code"

    def __init__(self, models: dict[Tier, str], *, executable: str | None = None, timeout: int = 900,
                 runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
                 sleep: Callable[[float], None] = time.sleep):
        self._exe = executable if executable and not os.path.isabs(executable) else find_claude(executable)
        if not self._exe:
            raise LLMError(
                "The `claude` command was not found. Install Claude Code (PowerShell: "
                "irm https://claude.ai/install.ps1 | iex), open a NEW terminal, run `claude` once to log in. "
                "If it is installed somewhere else, set CLAUDE_CODE_PATH in .env to the full path of claude.exe.")
        self._models, self._timeout, self._run, self._sleep = models, timeout, runner, sleep

    def generate(self, prompt: str, *, system: str | None = None, tier: Tier = "fast", search: bool = False,
                 json_schema: type[BaseModel] | None = None, max_tokens: int = 8192,
                 temperature: float | None = None) -> LLMResponse:
        if search:
            raise LLMError("Web research uses the free DuckDuckGo route, not the model")
        model = self._models[tier]
        cmd = [self._exe, "-p", "--output-format", "json", "--model", model, "--tools", "",
               "--no-session-persistence", "--system-prompt", system or JSON_SYSTEM]
        for attempt in range(1, 4):
            try:
                proc = self._run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                 timeout=self._timeout)
            except subprocess.TimeoutExpired as exc:
                raise LLMError(f"Claude Code did not answer within {self._timeout}s") from exc
            out = (proc.stdout or "").strip()
            try:
                data = json.loads(out[out.find("{"):]) if "{" in out else {}
            except json.JSONDecodeError:
                data = {}
            text = data.get("result") or ""
            if proc.returncode == 0 and not data.get("is_error") and text.strip():
                return LLMResponse(text=text, provider=self.name, model=model)
            detail = (text or proc.stderr or out or f"exit code {proc.returncode}").strip()[:300]
            if any(w in detail.lower() for w in ("usage limit", "limit reached", "rate limit")):
                raise LLMError(f"Claude plan usage limit reached; try again later. ({detail})")
            if any(w in detail.lower() for w in ("log in", "login", "authenticate", "/login")):
                raise LLMError(f"Claude Code is not logged in. Run `claude` once and log in. ({detail})")
            log.warning("Claude Code call failed (attempt %d): %s", attempt, detail)
            self._sleep(10 * attempt)
        raise LLMError(f"Claude Code failed after 3 attempts: {detail}")
