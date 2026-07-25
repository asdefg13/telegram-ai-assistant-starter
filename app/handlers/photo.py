"""Photos: download the largest size → vision model → persist as context."""

import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from app.services.vision import VisionService
from app.storage.base import Repositories
from app.storage.models import ChatMessage
from app.utils.files import FileTooLargeError, download_file
from app.utils.telegram import answer_long

logger = logging.getLogger(__name__)

router = Router(name="photo")


@router.message(F.photo)
async def handle_photo(
    message: Message,
    vision: VisionService,
    repositories: Repositories,
) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # message.photo is ordered smallest → largest; take the best available size.
    photo = message.photo[-1]
    try:
        image = await download_file(message.bot, photo.file_id)
    except FileTooLargeError:
        await message.answer("That image is too large for me to process.")
        return

    try:
        description = await vision.describe(image, caption=message.caption)
    except Exception:
        logger.exception("vision call failed for user=%s", message.from_user.id)
        await message.answer("I could not analyse that image. Please try another one.")
        return

    # Store the exchange as text so the following turns can refer back to it.
    user_note = message.caption or "[sent a photo]"
    await repositories.messages.add(
        ChatMessage(telegram_id=message.from_user.id, role="user", content=user_note, kind="photo")
    )
    await repositories.messages.add(
        ChatMessage(telegram_id=message.from_user.id, role="assistant", content=description)
    )

    await answer_long(message, description)
