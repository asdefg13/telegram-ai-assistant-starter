"""Repository contract tests.

They run against the in-memory implementation, but every assertion here is part
of the interface the Supabase implementation must honour too.
"""

from app.storage.models import ChatMessage, Note, User

from .conftest import TELEGRAM_ID


async def test_get_or_create_is_idempotent(repositories):
    first = await repositories.users.get_or_create(User(TELEGRAM_ID, username="client"))
    second = await repositories.users.get_or_create(User(TELEGRAM_ID, username="renamed"))

    assert first.username == "client"
    # Second call must not overwrite the stored profile.
    assert second.username == "client"
    assert (await repositories.users.get(TELEGRAM_ID)) is not None


async def test_unknown_user_is_none(repositories):
    assert await repositories.users.get(1) is None


async def test_recent_returns_chronological_tail(repositories):
    for index in range(10):
        await repositories.messages.add(
            ChatMessage(telegram_id=TELEGRAM_ID, role="user", content=f"msg-{index}")
        )

    recent = await repositories.messages.recent(TELEGRAM_ID, limit=3)

    assert [item.content for item in recent] == ["msg-7", "msg-8", "msg-9"]


async def test_messages_are_scoped_per_user(repositories):
    await repositories.messages.add(ChatMessage(TELEGRAM_ID, "user", "mine"))
    await repositories.messages.add(ChatMessage(999, "user", "theirs"))

    assert len(await repositories.messages.recent(TELEGRAM_ID)) == 1
    assert len(await repositories.messages.recent(999)) == 1


async def test_clear_reports_removed_count(repositories):
    await repositories.messages.add(ChatMessage(TELEGRAM_ID, "user", "a"))
    await repositories.messages.add(ChatMessage(TELEGRAM_ID, "assistant", "b"))

    assert await repositories.messages.clear(TELEGRAM_ID) == 2
    assert await repositories.messages.recent(TELEGRAM_ID) == []
    assert await repositories.messages.clear(TELEGRAM_ID) == 0


async def test_note_search_matches_text_and_tags(repositories):
    await repositories.notes.add(Note(TELEGRAM_ID, "Landlord is Ana", tags=["home"]))
    await repositories.notes.add(Note(TELEGRAM_ID, "Standup at 10:00", tags=["work"]))

    by_text = await repositories.notes.search(TELEGRAM_ID, "landlord")
    by_tag = await repositories.notes.search(TELEGRAM_ID, "work")
    missing = await repositories.notes.search(TELEGRAM_ID, "nothing here")

    assert [note.text for note in by_text] == ["Landlord is Ana"]
    assert [note.text for note in by_tag] == ["Standup at 10:00"]
    assert missing == []


async def test_empty_query_lists_notes_newest_first(repositories):
    await repositories.notes.add(Note(TELEGRAM_ID, "older"))
    await repositories.notes.add(Note(TELEGRAM_ID, "newer"))

    notes = await repositories.notes.search(TELEGRAM_ID, "")

    assert [note.text for note in notes] == ["newer", "older"]


async def test_stored_entities_get_an_id(repositories):
    note = await repositories.notes.add(Note(TELEGRAM_ID, "with id"))
    message = await repositories.messages.add(ChatMessage(TELEGRAM_ID, "user", "with id"))

    assert note.id and message.id
