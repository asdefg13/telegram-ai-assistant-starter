"""Domain models.

Plain dataclasses, deliberately decoupled from any storage engine: the same
objects cross the handler, agent and repository boundaries.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

MessageRole = Literal["user", "assistant"]
MessageKind = Literal["text", "voice", "photo"]


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class User:
    """A Telegram user known to the bot."""

    telegram_id: int
    username: str | None = None
    full_name: str | None = None
    language_code: str | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass(slots=True)
class ChatMessage:
    """One turn of a conversation, replayed as model context."""

    telegram_id: int
    role: MessageRole
    content: str
    kind: MessageKind = "text"
    created_at: datetime = field(default_factory=_now)
    id: str | None = None


@dataclass(slots=True)
class Note:
    """A fact the assistant was asked to remember."""

    telegram_id: int
    text: str
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    id: str | None = None
