from __future__ import annotations

from src.settings import Settings

from .base import LLM, LLMError


def build_llm(settings: Settings, provider: str | None = None) -> LLM:
    provider = (provider or settings.llm_provider).lower()
    if provider == "gemini":
        from .gemini import GeminiLLM

        return GeminiLLM(
            settings.gemini_keys,
            {"fast": settings.gemini_model_fast, "smart": settings.gemini_model_smart,
             "research": settings.gemini_model_research},
        )
    if provider == "anthropic":
        from .anthropic_client import ClaudeLLM

        return ClaudeLLM(
            settings.anthropic_key,
            {"fast": settings.anthropic_model_fast, "smart": settings.anthropic_model_smart,
             "research": settings.anthropic_model_smart},
        )
    if provider == "ollama":
        from .ollama import OllamaLLM

        return OllamaLLM(settings.ollama_host, settings.ollama_model)
    raise LLMError(f"Unknown LLM_PROVIDER '{provider}' (use gemini, anthropic or ollama)")
