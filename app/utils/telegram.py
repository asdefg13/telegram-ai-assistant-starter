"""Small helpers around Telegram's transport limits."""

from collections.abc import Iterator

from aiogram.types import Message

# Telegram rejects any single sendMessage payload above 4096 characters.
MAX_MESSAGE_LENGTH = 4096


def split_message(text: str, limit: int = MAX_MESSAGE_LENGTH) -> Iterator[str]:
    """Split ``text`` into Telegram-sized chunks, preferring line boundaries."""
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        cut = window.rfind("\n")
        if cut <= 0:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = limit
        yield remaining[:cut].rstrip()
        remaining = remaining[cut:].lstrip()
    if remaining:
        yield remaining


async def answer_long(message: Message, text: str) -> None:
    """Reply with ``text``, splitting it when it exceeds the Telegram limit."""
    for chunk in split_message(text):
        await message.answer(chunk)
