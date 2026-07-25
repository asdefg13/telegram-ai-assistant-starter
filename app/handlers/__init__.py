"""Handler routers.

Order matters: commands are matched first, and the catch-all text router last.
"""

from aiogram import Router

from app.handlers import commands, photo, text, voice


def build_router() -> Router:
    """Compose every feature router into the one the dispatcher receives."""
    root = Router(name="root")
    root.include_router(commands.router)
    root.include_router(voice.router)
    root.include_router(photo.router)
    root.include_router(text.router)
    return root


__all__ = ["build_router", "commands", "photo", "text", "voice"]
