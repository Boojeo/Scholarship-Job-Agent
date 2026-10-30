"""Local Ollama provider (free, offline). No web grounding."""
from __future__ import annotations

import httpx
from pydantic import BaseModel

from .base import LLM, LLMError, LLMResponse, Tier


class OllamaLLM(LLM):
    name = "ollama"

    def __init__(self, host: str, model: str, client: httpx.Client | None = None):
        self._host = host.rstrip("/")
        self._model = model
        self._http = client or httpx.Client(timeout=300)

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        tier: Tier = "fast",
        search: bool = False,
        json_schema: type[BaseModel] | None = None,
        max_tokens: int = 8192,
        temperature: float | None = None,
    ) -> LLMResponse:
        if search:
            raise LLMError("Ollama has no web search; use Gemini for the research step")
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens, **({"temperature": temperature} if temperature is not None else {})},
        }
        try:
            r = self._http.post(f"{self._host}/api/chat", json=body)
            r.raise_for_status()
            return LLMResponse(text=r.json()["message"]["content"], provider=self.name, model=self._model)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc
