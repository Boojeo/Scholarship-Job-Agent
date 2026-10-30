"""Gemini provider (google-genai SDK) with multi-key failover and optional Google Search grounding."""
from __future__ import annotations

import logging
import time
from typing import Callable

from pydantic import BaseModel

from .base import LLM, LLMError, LLMResponse, Tier

log = logging.getLogger(__name__)


class GeminiLLM(LLM):
    name = "gemini"

    def __init__(
        self,
        api_keys: list[str],
        models: dict[Tier, str],
        *,
        client_factory: Callable[[str], object] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 6,
    ):
        if not api_keys:
            raise LLMError("No Gemini API key configured. Set GEMINI_API_KEYS in .env")
        self._keys = list(api_keys)
        self._models = models
        self._sleep = sleep
        self._max_attempts = max_attempts
        self._factory = client_factory or self._default_factory
        self._active = 0
        self._clients: dict[str, object] = {}

    @staticmethod
    def _default_factory(key: str):
        _genai_modules()
        from google import genai

        return genai.Client(api_key=key)

    def _client(self):
        key = self._keys[self._active]
        if key not in self._clients:
            self._clients[key] = self._factory(key)
        return self._clients[key]

    def _rotate(self) -> bool:
        """Move to the next key. Returns True if we wrapped around to the first key again."""
        self._active = (self._active + 1) % len(self._keys)
        return self._active == 0

    def _drop_active_key(self) -> None:
        bad = self._keys.pop(self._active)
        self._clients.pop(bad, None)
        if not self._keys:
            raise LLMError("All Gemini API keys were rejected. Check GEMINI_API_KEYS in .env")
        self._active %= len(self._keys)

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
        errors, types = _genai_modules()
        model = self._models[tier]
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_tokens,
            tools=[types.Tool(google_search=types.GoogleSearch())] if search else None,
            response_mime_type="application/json" if json_schema else None,
            response_schema=json_schema,
        )
        backoff = 20.0
        for attempt in range(1, self._max_attempts + 1):
            try:
                resp = self._client().models.generate_content(model=model, contents=prompt, config=config)
                text = resp.text or ""
                if not text.strip():
                    raise LLMError(f"Gemini returned no text (model={model}); the answer may have been blocked")
                return LLMResponse(text=text, provider=self.name, model=model, sources=_grounding_urls(resp))
            except errors.ClientError as exc:
                code = getattr(exc, "code", None)
                if code == 429:
                    wrapped = self._rotate()
                    log.warning("Gemini quota hit (attempt %d); switched to key #%d", attempt, self._active + 1)
                    if wrapped:  # every key is exhausted for now: wait for the quota window
                        self._sleep(backoff)
                        backoff = min(backoff * 2, 120)
                elif code in (400, 401, 403) and "key" in str(exc).lower():
                    log.warning("Gemini key #%d rejected; dropping it", self._active + 1)
                    self._drop_active_key()
                elif code == 404:
                    raise LLMError(
                        f"Gemini model '{model}' not found. Run `python main.py models` and update GEMINI_MODEL_* in .env"
                    ) from exc
                else:
                    raise LLMError(f"Gemini request rejected ({code}): {exc}") from exc
            except errors.ServerError as exc:
                log.warning("Gemini server error (attempt %d): %s", attempt, exc)
                self._sleep(min(5.0 * attempt, 30))
        raise LLMError(f"Gemini failed after {self._max_attempts} attempts (model={model})")

    def list_models(self) -> list[str]:
        """Names of models the active key can use for generateContent."""
        names = []
        for m in self._client().models.list():
            actions = getattr(m, "supported_actions", None) or []
            if not actions or "generateContent" in actions:
                names.append((m.name or "").removeprefix("models/"))
        return sorted(names)


def _genai_modules():
    try:
        from google.genai import errors, types
    except ImportError as exc:
        raise LLMError(
            "The 'google-genai' package is not installed for this Python. Run: python -m pip install -r requirements.txt"
        ) from exc
    return errors, types


def _grounding_urls(resp) -> list[str]:
    urls: list[str] = []
    try:
        meta = resp.candidates[0].grounding_metadata
        for chunk in (meta.grounding_chunks or []) if meta else []:
            if chunk.web and chunk.web.uri:
                urls.append(chunk.web.uri)
    except (AttributeError, IndexError, TypeError):
        pass
    return urls
