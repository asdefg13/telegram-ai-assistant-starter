"""Storage layer — the only module that knows which database is behind it."""

from app.config import Settings
from app.storage.base import (
    MessageRepository,
    NoteRepository,
    Repositories,
    UserRepository,
)
from app.storage.memory_repo import build_memory_repositories
from app.storage.models import ChatMessage, Note, User

__all__ = [
    "ChatMessage",
    "MessageRepository",
    "Note",
    "NoteRepository",
    "Repositories",
    "User",
    "UserRepository",
    "build_memory_repositories",
    "build_repositories",
]


def build_repositories(settings: Settings) -> Repositories:
    """Return the storage bundle selected by ``STORAGE_BACKEND``."""
    if settings.storage_backend == "memory":
        return build_memory_repositories()

    # Imported lazily so the memory backend does not require the supabase extra.
    from app.storage.supabase_repo import build_supabase_repositories

    assert settings.supabase_url and settings.supabase_service_key  # enforced in Settings
    return build_supabase_repositories(settings.supabase_url, settings.supabase_service_key)
