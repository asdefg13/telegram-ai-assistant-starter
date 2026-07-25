"""Per-user rate limiting.

Each turn costs an OpenAI call, so an impatient user tapping send five times
should not multiply the bill. In-process state is deliberate: with more than one
replica, back this with Redis.
"""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Drop messages that arrive faster than ``rate_limit`` seconds apart."""

    def __init__(self, rate_limit: float = 0.7, *, warn_after: int = 3) -> None:
        self._rate_limit = rate_limit
        self._warn_after = warn_after
        self._last_seen: dict[int, float] = {}
        self._strikes: dict[int, int] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        if not isinstance(event, Message) or from_user is None:
            return await handler(event, data)

        now = time.monotonic()
        previous = self._last_seen.get(from_user.id)
        self._last_seen[from_user.id] = now

        if previous is not None and now - previous < self._rate_limit:
            strikes = self._strikes.get(from_user.id, 0) + 1
            self._strikes[from_user.id] = strikes
            logger.debug("throttled user=%s strikes=%s", from_user.id, strikes)
            # Warn once, then stay silent so we do not amplify the flood.
            if strikes == self._warn_after:
                await event.answer("Too fast — give me a moment to answer.")
            return None

        self._strikes.pop(from_user.id, None)
        return await handler(event, data)
