"""Conversation service: persistence and history windowing."""

import contextlib

from app.storage.models import ChatMessage, Note

from .conftest import TELEGRAM_ID, make_completion


async def test_both_turns_are_persisted(conversation, openai_client, repositories):
    openai_client.chat.completions.create.return_value = make_completion("Sure.")

    await conversation.handle(telegram_id=TELEGRAM_ID, text="hello")

    stored = await repositories.messages.recent(TELEGRAM_ID)
    assert [(item.role, item.content) for item in stored] == [
        ("user", "hello"),
        ("assistant", "Sure."),
    ]


async def test_media_kind_is_recorded(conversation, openai_client, repositories):
    openai_client.chat.completions.create.return_value = make_completion("Sure.")

    await conversation.handle(telegram_id=TELEGRAM_ID, text="transcript", kind="voice")

    stored = await repositories.messages.recent(TELEGRAM_ID)
    assert stored[0].kind == "voice"
    assert stored[1].kind == "text"  # the reply itself is always text


async def test_history_window_is_capped(conversation, openai_client, repositories):
    openai_client.chat.completions.create.return_value = make_completion("ok")
    for index in range(10):
        await repositories.messages.add(ChatMessage(TELEGRAM_ID, "user", f"old-{index}"))

    await conversation.handle(telegram_id=TELEGRAM_ID, text="new")

    messages = openai_client.chat.completions.create.await_args.kwargs["messages"]
    # system + history_limit(4) + the new prompt
    assert len(messages) == 6
    assert messages[1]["content"] == "old-6"


async def test_failed_turn_does_not_pollute_history(conversation, openai_client, repositories):
    openai_client.chat.completions.create.side_effect = RuntimeError("openai is down")

    with contextlib.suppress(RuntimeError):
        await conversation.handle(telegram_id=TELEGRAM_ID, text="hello")

    assert await repositories.messages.recent(TELEGRAM_ID) == []


async def test_reset_clears_messages_but_keeps_notes(conversation, openai_client, repositories):
    openai_client.chat.completions.create.return_value = make_completion("ok")
    await conversation.handle(telegram_id=TELEGRAM_ID, text="hello")
    await repositories.notes.add(Note(TELEGRAM_ID, "keep me"))

    removed = await conversation.reset(TELEGRAM_ID)

    assert removed == 2
    assert await repositories.messages.recent(TELEGRAM_ID) == []
    assert len(await repositories.notes.search(TELEGRAM_ID, "")) == 1
