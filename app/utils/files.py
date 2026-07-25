"""Helpers for pulling media out of the Telegram Bot API."""

import io

from aiogram import Bot

# Telegram itself caps bot downloads at 20 MB; refuse earlier to keep memory flat.
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


class FileTooLargeError(RuntimeError):
    """Raised when a user sends media the bot refuses to buffer in memory."""


async def download_file(bot: Bot, file_id: str) -> bytes:
    """Download a Telegram file into memory and return its bytes."""
    file = await bot.get_file(file_id)
    if file.file_size and file.file_size > MAX_DOWNLOAD_BYTES:
        raise FileTooLargeError(f"file {file_id} is {file.file_size} bytes")

    buffer = io.BytesIO()
    await bot.download_file(file.file_path, buffer)
    return buffer.getvalue()
