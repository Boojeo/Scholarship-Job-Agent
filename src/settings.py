"""Environment-driven settings. Secrets only ever come from .env / the process environment."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def _split(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "claude_code"
    claude_code_model_fast: str = "haiku"
    claude_code_model_smart: str = "sonnet"
    claude_code_path: str = ""
    screen_provider: str = "claude_code"
    write_provider: str = "claude_code"
    gemini_keys: list[str] = field(default_factory=list)
    gemini_model_fast: str = "gemini-3.8-flash"
    gemini_model_smart: str = "gemini-3.8-flash"
    gemini_model_research: str = "gemini-3.8-flash"
    anthropic_key: str = ""
    anthropic_model_fast: str = "claude-haiku-5-5"
    anthropic_model_smart: str = "claude-sonnet-5-5"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    candidate_email: str = ""
    candidate_phone: str = ""
    timezone: str = "Asia/Riyadh"
    db_path: Path = ROOT / "data" / "autopilot.sqlite3"
    data_dir: Path = ROOT / "data"
    research_delay_seconds: float = 8.0
    telegram_token: str = ""
    telegram_owner_id: int | None = None
    digest_time: str = "09:00"
    match_threshold: int = 60
    vault_dir: Path = ROOT / "vault"
    kits_dir: Path = ROOT / "ready_to_apply"

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        load_dotenv(env_file or ROOT / ".env")
        e = os.environ.get
        keys = _split(e("GEMINI_API_KEYS", "") or e("GEMINI_API_KEY", ""))
        data_dir = ROOT / e("DATA_DIR", "data")
        return cls(
            llm_provider=e("LLM_PROVIDER", "claude_code").lower(),
            claude_code_model_fast=e("CLAUDE_CODE_MODEL_FAST", "haiku"),
            claude_code_model_smart=e("CLAUDE_CODE_MODEL_SMART", "sonnet"),
            claude_code_path=e("CLAUDE_CODE_PATH", ""),
            screen_provider=(e("SCREEN_PROVIDER") or e("LLM_PROVIDER") or "claude_code").lower(),
            write_provider=(e("WRITE_PROVIDER") or e("LLM_PROVIDER") or "claude_code").lower(),
            gemini_keys=keys,
            gemini_model_fast=e("GEMINI_MODEL_FAST", cls.gemini_model_fast),
            gemini_model_smart=e("GEMINI_MODEL_SMART", cls.gemini_model_smart),
            gemini_model_research=e("GEMINI_MODEL_RESEARCH", cls.gemini_model_research),
            anthropic_key=e("ANTHROPIC_API_KEY", ""),
            anthropic_model_fast=e("ANTHROPIC_MODEL_FAST", cls.anthropic_model_fast),
            anthropic_model_smart=e("ANTHROPIC_MODEL_SMART", cls.anthropic_model_smart),
            ollama_host=e("OLLAMA_HOST", cls.ollama_host),
            ollama_model=e("OLLAMA_MODEL", cls.ollama_model),
            candidate_email=e("CANDIDATE_EMAIL", ""),
            candidate_phone=e("CANDIDATE_PHONE", ""),
            timezone=e("CANDIDATE_TIMEZONE", cls.timezone),
            db_path=ROOT / e("DB_PATH", "data/autopilot.sqlite3"),
            data_dir=data_dir,
            research_delay_seconds=float(e("RESEARCH_DELAY_SECONDS", "8")),
            telegram_token=e("TELEGRAM_BOT_TOKEN", ""),
            telegram_owner_id=int(e("TELEGRAM_OWNER_ID")) if (e("TELEGRAM_OWNER_ID") or "").strip().isdigit() else None,
            digest_time=e("DIGEST_TIME", "09:00"),
            match_threshold=int(e("MATCH_THRESHOLD", "60")),
        )
