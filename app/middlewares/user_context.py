"""Middleware that guarantees every handler sees a persisted user."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.storage.base import Repositories
from app.storage.models import User

logger = logging.getLogger(__name__)


class UserContextMiddleware(BaseMiddleware):
    """Upsert the Telegram user and inject it into handler data as ``user``."""

    def __init__(self, repositories: Repositories) -> None:
        self._repositories = repositories

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        if isinstance(event, Message) and from_user is not None:
            user = await self._repositories.users.get_or_create(
                User(
                    telegram_id=from_user.id,
                    username=from_user.username,
                    full_name=from_user.full_name,
                    language_code=from_user.language_code,
                )
            )
            data["user"] = user

        return await handler(event, data)
