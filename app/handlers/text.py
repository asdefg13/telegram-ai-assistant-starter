"""Plain text messages — the main path into the agent."""

import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from app.services.conversation import ConversationService
from app.utils.telegram import answer_long

logger = logging.getLogger(__name__)

router = Router(name="text")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, conversation: ConversationService) -> None:
    """Send the message to the agent and stream the answer back."""
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        reply = await conversation.handle(
            telegram_id=message.from_user.id,
            text=message.text,
            kind="text",
        )
    except Exception:
        logger.exception("text turn failed for user=%s", message.from_user.id)
        await message.answer("Something broke on my side. Please try again in a moment.")
        return

    await answer_long(message, reply.text)
