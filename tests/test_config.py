"""Settings validation — misconfiguration must fail at boot, not at runtime."""

import pytest
from pydantic import ValidationError

from app.config import Settings

MANAGED_VARS = (
    "BOT_TOKEN",
    "OPENAI_API_KEY",
    "STORAGE_BACKEND",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "HISTORY_LIMIT",
)


@pytest.fixture
def env(monkeypatch):
    """Start from a clean environment and let each test add what it needs."""
    for key in MANAGED_VARS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("BOT_TOKEN", "0000000000:test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    return monkeypatch


def _settings() -> Settings:
    # _env_file=None keeps a developer's local .env out of the test run.
    return Settings(_env_file=None)


def test_supabase_backend_requires_credentials(env):
    env.setenv("STORAGE_BACKEND", "supabase")

    with pytest.raises(ValidationError, match="SUPABASE_URL"):
        _settings()


def test_supabase_backend_accepts_full_credentials(env):
    env.setenv("STORAGE_BACKEND", "supabase")
    env.setenv("SUPABASE_URL", "https://example.supabase.co")
    env.setenv("SUPABASE_SERVICE_KEY", "service-key")

    assert _settings().storage_backend == "supabase"


def test_memory_backend_needs_no_database(env):
    env.setenv("STORAGE_BACKEND", "memory")

    settings = _settings()

    assert settings.storage_backend == "memory"
    assert settings.supabase_url is None


def test_missing_required_secrets_fail_fast(env):
    env.delenv("BOT_TOKEN")
    env.setenv("STORAGE_BACKEND", "memory")

    with pytest.raises(ValidationError, match="bot_token"):
        _settings()


def test_unknown_backend_is_rejected(env):
    env.setenv("STORAGE_BACKEND", "mongodb")

    with pytest.raises(ValidationError):
        _settings()


def test_numeric_values_are_coerced_from_strings(env):
    env.setenv("STORAGE_BACKEND", "memory")
    env.setenv("HISTORY_LIMIT", "20")

    settings = _settings()

    assert settings.history_limit == 20
    assert settings.agent_max_iterations > 0
    assert settings.openai_model
