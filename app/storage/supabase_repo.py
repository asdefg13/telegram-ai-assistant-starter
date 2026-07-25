"""Supabase (Postgres) repository implementations.

The official ``supabase`` client is synchronous, so every call is pushed onto a
worker thread with :func:`asyncio.to_thread`. That keeps the aiogram event loop
free while still using the supported client.

Schema lives in ``supabase/schema.sql``.
"""

import asyncio
from datetime import datetime
from typing import Any

from app.storage.base import (
    MessageRepository,
    NoteRepository,
    Repositories,
    UserRepository,
)
from app.storage.models import ChatMessage, Note, User
from supabase import Client, create_client

USERS_TABLE = "users"
MESSAGES_TABLE = "messages"
NOTES_TABLE = "notes"


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    # Postgres returns "2026-07-26T10:00:00+00:00" or "...Z"
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class SupabaseUserRepository(UserRepository):
    def __init__(self, client: Client) -> None:
        self._client = client

    def _row_to_user(self, row: dict[str, Any]) -> User:
        user = User(
            telegram_id=row["telegram_id"],
            username=row.get("username"),
            full_name=row.get("full_name"),
            language_code=row.get("language_code"),
        )
        created_at = _parse_timestamp(row.get("created_at"))
        if created_at:
            user.created_at = created_at
        return user

    async def get_or_create(self, user: User) -> User:
        existing = await self.get(user.telegram_id)
        if existing:
            return existing

        payload = {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "full_name": user.full_name,
            "language_code": user.language_code,
        }
        response = await asyncio.to_thread(
            lambda: (
                self._client.table(USERS_TABLE).upsert(payload, on_conflict="telegram_id").execute()
            )
        )
        rows = response.data or [payload]
        return self._row_to_user(rows[0])

    async def get(self, telegram_id: int) -> User | None:
        response = await asyncio.to_thread(
            lambda: (
                self._client.table(USERS_TABLE)
                .select("*")
                .eq("telegram_id", telegram_id)
                .limit(1)
                .execute()
            )
        )
        rows = response.data or []
        return self._row_to_user(rows[0]) if rows else None


class SupabaseMessageRepository(MessageRepository):
    def __init__(self, client: Client) -> None:
        self._client = client

    def _row_to_message(self, row: dict[str, Any]) -> ChatMessage:
        message = ChatMessage(
            telegram_id=row["telegram_id"],
            role=row["role"],
            content=row["content"],
            kind=row.get("kind", "text"),
            id=str(row["id"]) if row.get("id") is not None else None,
        )
        created_at = _parse_timestamp(row.get("created_at"))
        if created_at:
            message.created_at = created_at
        return message

    async def add(self, message: ChatMessage) -> ChatMessage:
        payload = {
            "telegram_id": message.telegram_id,
            "role": message.role,
            "content": message.content,
            "kind": message.kind,
        }
        response = await asyncio.to_thread(
            lambda: self._client.table(MESSAGES_TABLE).insert(payload).execute()
        )
        rows = response.data or []
        return self._row_to_message(rows[0]) if rows else message

    async def recent(self, telegram_id: int, limit: int = 12) -> list[ChatMessage]:
        response = await asyncio.to_thread(
            lambda: (
                self._client.table(MESSAGES_TABLE)
                .select("*")
                .eq("telegram_id", telegram_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
        )
        rows = response.data or []
        # Fetched newest-first for the LIMIT to be meaningful; replay oldest-first.
        return [self._row_to_message(row) for row in reversed(rows)]

    async def clear(self, telegram_id: int) -> int:
        response = await asyncio.to_thread(
            lambda: (
                self._client.table(MESSAGES_TABLE).delete().eq("telegram_id", telegram_id).execute()
            )
        )
        return len(response.data or [])


class SupabaseNoteRepository(NoteRepository):
    def __init__(self, client: Client) -> None:
        self._client = client

    def _row_to_note(self, row: dict[str, Any]) -> Note:
        note = Note(
            telegram_id=row["telegram_id"],
            text=row["text"],
            tags=list(row.get("tags") or []),
            id=str(row["id"]) if row.get("id") is not None else None,
        )
        created_at = _parse_timestamp(row.get("created_at"))
        if created_at:
            note.created_at = created_at
        return note

    async def add(self, note: Note) -> Note:
        payload = {
            "telegram_id": note.telegram_id,
            "text": note.text,
            "tags": note.tags,
        }
        response = await asyncio.to_thread(
            lambda: self._client.table(NOTES_TABLE).insert(payload).execute()
        )
        rows = response.data or []
        return self._row_to_note(rows[0]) if rows else note

    async def search(self, telegram_id: int, query: str, limit: int = 5) -> list[Note]:
        needle = query.strip()
        builder = (
            self._client.table(NOTES_TABLE)
            .select("*")
            .eq("telegram_id", telegram_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if needle:
            # ILIKE keeps this dependency-free; swap for pgvector when semantic
            # recall starts to matter.
            builder = builder.ilike("text", f"%{needle}%")

        response = await asyncio.to_thread(builder.execute)
        return [self._row_to_note(row) for row in response.data or []]


def build_supabase_repositories(url: str, service_key: str) -> Repositories:
    """Build the Supabase-backed storage bundle."""
    client = create_client(url, service_key)
    return Repositories(
        users=SupabaseUserRepository(client),
        messages=SupabaseMessageRepository(client),
        notes=SupabaseNoteRepository(client),
    )
