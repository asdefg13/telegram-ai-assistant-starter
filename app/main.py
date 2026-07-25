"""Entrypoint: `python -m app.main`."""

import asyncio
import logging

from app.bot import build_application
from app.config import get_settings
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    application = build_application(settings)
    try:
        me = await application.bot.get_me()
        logger.info("starting long polling as @%s", me.username)
        # Drop the backlog so a restart does not replay hours of old messages.
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.dispatcher.start_polling(application.bot)
    finally:
        await application.aclose()
        logger.info("shutdown complete")


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("interrupted")


if __name__ == "__main__":
    main()
