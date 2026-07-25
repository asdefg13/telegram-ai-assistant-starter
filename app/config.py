"""Typed application settings.

Everything the bot needs comes from environment variables (or a local ``.env``),
so the same image runs unchanged in dev, staging and production.
"""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

StorageBackend = Literal["supabase", "memory"]


class Settings(BaseSettings):
    """Validated runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    bot_token: str

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o-mini"
    openai_transcription_model: str = "whisper-1"

    # Storage
    storage_backend: StorageBackend = "supabase"
    supabase_url: str | None = None
    supabase_service_key: str | None = None

    # Behaviour
    history_limit: int = 12
    agent_max_iterations: int = 5
    rate_limit_seconds: float = 0.7
    log_level: str = "INFO"

    @model_validator(mode="after")
    def _require_supabase_credentials(self) -> "Settings":
        if self.storage_backend == "supabase" and not (
            self.supabase_url and self.supabase_service_key
        ):
            raise ValueError(
                "STORAGE_BACKEND=supabase requires SUPABASE_URL and SUPABASE_SERVICE_KEY"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide settings, parsed once."""
    return Settings()  # type: ignore[call-arg]
