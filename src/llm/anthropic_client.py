"""Anthropic (Claude) provider. Optional: used when ANTHROPIC_API_KEY is set."""
from __future__ import annotations

import logging

import anthropic
from pydantic import BaseModel

from .base import LLM, LLMError, LLMResponse, Tier

log = logging.getLogger(__name__)


class ClaudeLLM(LLM):
    name = "anthropic"

    def __init__(self, api_key: str, models: dict[Tier, str], client: anthropic.Anthropic | None = None):
        if not api_key and client is None:
            raise LLMError("No Anthropic API key configured. Set ANTHROPIC_API_KEY in .env")
        self._client = client or anthropic.Anthropic(api_key=api_key)
        self._models = models

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
            raise LLMError("Web-grounded research is run through Gemini; Claude is used for screening and writing")
        model = self._models["smart" if tier == "research" else tier]
        kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        # temperature is deliberately never sent: current Claude models reject non-default sampling params.
        try:
            msg = self._client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            raise LLMError(f"Claude rate limit: {exc}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(f"Claude connection error: {exc}") from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Claude request failed ({exc.status_code}): {exc.message}") from exc
        if msg.stop_reason == "refusal":
            raise LLMError("Claude declined this request")
        text = "".join(b.text for b in msg.content if b.type == "text")
        return LLMResponse(text=text, provider=self.name, model=model)
