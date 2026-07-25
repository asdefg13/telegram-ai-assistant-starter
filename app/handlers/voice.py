"""Voice notes: download → Whisper → agent."""

import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from app.services.conversation import ConversationService
from app.services.transcription import TranscriptionError, TranscriptionService
from app.utils.files import FileTooLargeError, download_file
from app.utils.telegram import answer_long

logger = logging.getLogger(__name__)

router = Router(name="voice")


@router.message(F.voice | F.audio)
async def handle_voice(
    message: Message,
    conversation: ConversationService,
    transcription: TranscriptionService,
) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    media = message.voice or message.audio

    try:
        audio = await download_file(message.bot, media.file_id)
    except FileTooLargeError:
        await message.answer("That audio file is too large for me to process.")
        return

    try:
        text = await transcription.transcribe(audio)
    except TranscriptionError:
        logger.warning("empty transcription for user=%s", message.from_user.id)
        await message.answer("I could not make out any speech there. Try recording again?")
        return

    # Echo the transcript so the user can see what the model actually heard.
    await message.answer(f"🎙 <i>{text}</i>")

    try:
        reply = await conversation.handle(
            telegram_id=message.from_user.id,
            text=text,
            kind="voice",
        )
    except Exception:
        logger.exception("voice turn failed for user=%s", message.from_user.id)
        await message.answer("Something broke on my side. Please try again in a moment.")
        return

    await answer_long(message, reply.text)
