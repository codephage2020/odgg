"""Application configuration via environment variables."""

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
    llm_timeout: int = 30  # seconds

    # CORS
    cors_origins: list[str] = ["http://localhost:3001"]

    model_config = {"env_prefix": "ODGG_", "env_file": ".env"}


settings = Settings()
