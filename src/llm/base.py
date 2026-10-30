"""Provider-neutral LLM interface used by every other module."""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal, TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError

Tier = Literal["fast", "smart", "research"]
T = TypeVar("T")


class LLMError(RuntimeError):
    """Raised when a provider call cannot be completed (after retries and key rotation)."""


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    sources: list[str] = field(default_factory=list)  # grounding URLs, informational only


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str):
    """Parse JSON from model output that may be wrapped in prose or code fences."""
    candidates = [text.strip()] + [m.strip() for m in _FENCE.findall(text)]
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            pass
    # Fall back to the outermost array/object in the text.
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start, end = text.find(open_ch), text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no valid JSON found in model output")


class LLM(ABC):
    name = "base"

    @abstractmethod
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
        """One model call. `search=True` asks the provider to ground the answer in live web search
        (only some providers support it; others raise LLMError)."""

    def generate_json(
        self,
        prompt: str,
        item_type: type[T],
        *,
        system: str | None = None,
        tier: Tier = "fast",
        many: bool = True,
        max_tokens: int = 16384,
    ) -> list[T] | T:
        """Call the model and validate the answer against a pydantic type. One repair attempt."""
        adapter = TypeAdapter(list[item_type] if many else item_type)
        suffix = "\n\nReturn ONLY valid JSON. No prose, no markdown fences."
        last_error = ""
        for attempt in range(2):
            ask = prompt + suffix if attempt == 0 else (
                f"{prompt}{suffix}\n\nYour previous answer was invalid: {last_error}\nFix it and answer again."
            )
            resp = self.generate(ask, system=system, tier=tier, max_tokens=max_tokens, temperature=0.0)
            try:
                return adapter.validate_python(extract_json(resp.text))
            except (ValueError, ValidationError) as exc:
                last_error = str(exc)[:400]
        raise LLMError(f"model did not return valid JSON after repair: {last_error}")
