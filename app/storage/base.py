"""Repository interfaces.

Handlers and the agent depend on these abstractions only. Swapping Supabase for
Postgres, Mongo or an in-memory fake is a one-line change in
:func:`app.storage.build_repositories` — no call site moves.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.storage.models import ChatMessage, Note, User


class UserRepository(ABC):
    """Persistence for Telegram user profiles."""

    @abstractmethod
    async def get_or_create(self, user: User) -> User:
        """Return the stored user, inserting it on first contact."""

    @abstractmethod
    async def get(self, telegram_id: int) -> User | None:
        """Return the stored user or ``None``."""


class MessageRepository(ABC):
    """Persistence for conversation history."""

    @abstractmethod
    async def add(self, message: ChatMessage) -> ChatMessage:
        """Append one message to the conversation."""

    @abstractmethod
    async def recent(self, telegram_id: int, limit: int = 12) -> list[ChatMessage]:
        """Return the last ``limit`` messages in chronological order."""

    @abstractmethod
    async def clear(self, telegram_id: int) -> int:
        """Drop the conversation and return how many messages were removed."""


class NoteRepository(ABC):
    """Persistence for user notes — the assistant's long-term memory."""

    @abstractmethod
    async def add(self, note: Note) -> Note:
        """Store a note."""

    @abstractmethod
    async def search(self, telegram_id: int, query: str, limit: int = 5) -> list[Note]:
        """Return notes matching ``query``, newest first."""


@dataclass(slots=True)
class Repositories:
    """Everything the application needs from storage, in one injectable bundle."""

    users: UserRepository
    messages: MessageRepository
    notes: NoteRepository
