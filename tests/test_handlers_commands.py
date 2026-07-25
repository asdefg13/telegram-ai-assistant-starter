"""Command handlers."""

from app.handlers.commands import handle_help, handle_reset, handle_start

from .conftest import TELEGRAM_ID


async def test_start_explains_the_three_input_modes(message, answered):
    await handle_start(message)

    text = answered()[0]
    assert "voice note" in text
    assert "photo" in text
    assert "/reset" in text


async def test_help_lists_the_registered_tools(message, answered):
    await handle_help(message)

    text = answered()[0]
    for tool in ("get_weather", "save_note", "search_notes"):
        assert tool in text


async def test_reset_clears_history_and_reports_the_count(message, answered, fake_conversation):
    await handle_reset(message, fake_conversation)

    fake_conversation.reset.assert_awaited_once_with(TELEGRAM_ID)
    assert "Cleared 7 message(s)" in answered()[0]
