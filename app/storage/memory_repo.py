"""In-memory repositories.

Used by the test suite and by ``STORAGE_BACKEND=memory`` for a zero-infra local
run. State lives for the lifetime of the process and is intentionally lost on
restart.
"""

import uuid
from collections import defaultdict

from app.storage.base import (
    MessageRepository,
    NoteRepository,
    Repositories,
    UserRepository,
)
from app.storage.models import ChatMessage, Note, User


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[int, User] = {}

    async def get_or_create(self, user: User) -> User:
        return self._users.setdefault(user.telegram_id, user)

    async def get(self, telegram_id: int) -> User | None:
        return self._users.get(telegram_id)


class InMemoryMessageRepository(MessageRepository):
    def __init__(self) -> None:
        self._messages: dict[int, list[ChatMessage]] = defaultdict(list)

    async def add(self, message: ChatMessage) -> ChatMessage:
        message.id = message.id or str(uuid.uuid4())
        self._messages[message.telegram_id].append(message)
        return message

    async def recent(self, telegram_id: int, limit: int = 12) -> list[ChatMessage]:
        return self._messages[telegram_id][-limit:]

    async def clear(self, telegram_id: int) -> int:
        removed = len(self._messages[telegram_id])
        self._messages[telegram_id].clear()
        return removed


class InMemoryNoteRepository(NoteRepository):
    def __init__(self) -> None:
        self._notes: dict[int, list[Note]] = defaultdict(list)

    async def add(self, note: Note) -> Note:
        note.id = note.id or str(uuid.uuid4())
        self._notes[note.telegram_id].append(note)
        return note

    async def search(self, telegram_id: int, query: str, limit: int = 5) -> list[Note]:
        needle = query.strip().lower()
        matches = [
            note
            for note in reversed(self._notes[telegram_id])
            if not needle
            or needle in note.text.lower()
            or any(needle in tag.lower() for tag in note.tags)
        ]
        return matches[:limit]


def build_memory_repositories() -> Repositories:
    """Build a fresh, isolated in-memory storage bundle."""
    return Repositories(
        users=InMemoryUserRepository(),
        messages=InMemoryMessageRepository(),
        notes=InMemoryNoteRepository(),
    )
