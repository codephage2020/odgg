"""Application configuration via environment variables with runtime override support."""

from __future__ import annotations

from typing import Any

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "ODGG"
    debug: bool = False

    # Database for session storage (SQLite)
    session_db_url: str = "sqlite+aiosqlite:///./odgg_sessions.db"

    # LLM settings
    llm_provider: str = "openai"  # openai | ollama | anthropic | etc.
    llm_model: str = "gpt-4o"
    llm_api_key: str = ""
    llm_base_url: str = ""  # For Ollama: http://localhost:11434
    llm_timeout: int = 120  # seconds — Kimi and other models can take 60s+

    # CORS
    cors_origins: list[str] = ["http://localhost:3001"]

    model_config = {"env_prefix": "ODGG_", "env_file": ".env"}


settings = Settings()

# ---------------------------------------------------------------------------
# Runtime LLM config overrides (populated from DB, updated via API)
# ---------------------------------------------------------------------------

_runtime_overrides: dict[str, Any] = {}


def get_llm_config() -> dict[str, Any]:
    """Return effective LLM config, merging runtime overrides over env defaults."""
    return {
        "provider": _runtime_overrides.get("provider") or settings.llm_provider,
        "model": _runtime_overrides.get("model") or settings.llm_model,
        "api_key": _runtime_overrides.get("api_key") or settings.llm_api_key,
        "base_url": _runtime_overrides.get("base_url") or settings.llm_base_url,
        "timeout": _runtime_overrides.get("timeout") or settings.llm_timeout,
    }


def get_llm_config_sources() -> dict[str, str]:
    """Return the source ('env' or 'user') for each LLM config field."""
    fields = ["provider", "model", "api_key", "base_url", "timeout"]
    return {f: "user" if _runtime_overrides.get(f) else "env" for f in fields}


def update_runtime_overrides(overrides: dict[str, Any]) -> None:
    """Merge non-None values into runtime overrides."""
    for key, value in overrides.items():
        if value is not None:
            _runtime_overrides[key] = value


def clear_runtime_overrides() -> None:
    """Reset to environment variable defaults."""
    _runtime_overrides.clear()
