from __future__ import annotations

from src.settings import Settings

from .base import LLM, FallbackLLM, LLMError


def build_llm(settings: Settings, provider: str | None = None) -> LLM:
    provider = (provider or settings.llm_provider).lower()
    if provider in ("claude_code", "claude"):
        from .claude_code import ClaudeCodeLLM

        return ClaudeCodeLLM({"fast": settings.claude_code_model_fast, "smart": settings.claude_code_model_smart,
                              "research": settings.claude_code_model_smart},
                             executable=settings.claude_code_path or None)
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
    raise LLMError(f"Unknown LLM_PROVIDER '{provider}' (use claude_code, gemini, anthropic or ollama)")


def build_role_llm(settings: Settings, role: str) -> LLM:
    """role 'screen' = daily filtering (many cheap calls), 'write' = CV/letters (few, quality matters).
    Each role has its own provider; when the two differ, the other one is the automatic backup."""
    main = settings.screen_provider if role == "screen" else settings.write_provider
    other = settings.write_provider if role == "screen" else settings.screen_provider
    primary = build_llm(settings, main)
    if other == main:
        return primary
    if hasattr(primary, "_max_attempts"):
        primary._max_attempts = 3  # give up sooner on quota errors: the backup takes over
    try:
        return FallbackLLM(primary, build_llm(settings, other))
    except LLMError:
        return primary
