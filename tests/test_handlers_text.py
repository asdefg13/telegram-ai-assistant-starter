"""Text handler: happy path, transport limits and failure isolation."""

from app.handlers.text import handle_text
from app.utils.telegram import MAX_MESSAGE_LENGTH, split_message

from .conftest import TELEGRAM_ID


async def test_text_is_forwarded_to_the_agent(message, answered, fake_conversation):
    message.text = "what is the weather in Lisbon?"

    await handle_text(message, fake_conversation)

    fake_conversation.handle.assert_awaited_once_with(
        telegram_id=TELEGRAM_ID, text="what is the weather in Lisbon?", kind="text"
    )
    assert answered() == ["Answer from the agent."]


async def test_typing_indicator_is_sent_first(message, fake_conversation):
    message.text = "hi"

    await handle_text(message, fake_conversation)

    message.bot.send_chat_action.assert_awaited_once()
    assert message.bot.send_chat_action.await_args.kwargs["chat_id"] == TELEGRAM_ID


async def test_long_answers_are_split_into_valid_chunks(message, answered, fake_conversation):
    message.text = "write me an essay"
    fake_conversation.handle.return_value.text = "\n".join(
        f"line {index} " + "x" * 80 for index in range(200)
    )

    await handle_text(message, fake_conversation)

    chunks = answered()
    assert len(chunks) > 1
    assert all(len(chunk) <= MAX_MESSAGE_LENGTH for chunk in chunks)


async def test_agent_failure_becomes_a_friendly_message(message, answered, fake_conversation):
    message.text = "hi"
    fake_conversation.handle.side_effect = RuntimeError("openai is down")

    await handle_text(message, fake_conversation)  # must not raise

    assert "Something broke on my side" in answered()[0]


def test_split_message_never_loses_content():
    text = " ".join(f"word{index}" for index in range(2000))

    chunks = list(split_message(text))

    assert len(chunks) > 1
    # Whitespace at the cut points is trimmed; no word may be lost or halved.
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")
