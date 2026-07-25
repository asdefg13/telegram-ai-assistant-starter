"""Slash commands."""

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.services.conversation import ConversationService

logger = logging.getLogger(__name__)

router = Router(name="commands")

START_TEXT = (
    "Hi! I am an AI assistant.\n\n"
    "• Send me text and I will answer, calling tools when it helps.\n"
    "• Send a voice note — I transcribe it and reply.\n"
    "• Send a photo — I can read and describe it.\n\n"
    "Try: “remember that my landlord is called Ana” and later “who is my landlord?”.\n\n"
    "/help — what I can do\n"
    "/reset — forget our conversation"
)

HELP_TEXT = (
    "What I can do:\n\n"
    "1. get_weather — live conditions for any city.\n"
    "2. save_note — remember a fact you tell me.\n"
    "3. search_notes — recall what you told me earlier.\n\n"
    "Voice notes go through Whisper; photos go through a vision model.\n"
    "/reset clears the conversation history. Your notes are kept."
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(START_TEXT)


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("reset"))
async def handle_reset(message: Message, conversation: ConversationService) -> None:
    removed = await conversation.reset(message.from_user.id)
    logger.info("reset user=%s removed=%s", message.from_user.id, removed)
    await message.answer(f"Cleared {removed} message(s). Your notes are untouched.")
