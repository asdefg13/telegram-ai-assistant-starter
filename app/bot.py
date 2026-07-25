"""Composition root.

Every dependency is built exactly once, here, and injected downwards. Nothing
below this module imports settings or constructs a client of its own — which is
what makes the handlers and services trivially testable.
"""

import logging
from dataclasses import dataclass

import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from openai import AsyncOpenAI

from app.config import Settings
from app.handlers import build_router
from app.middlewares import ThrottlingMiddleware, UserContextMiddleware
from app.services.agent import AgentService
from app.services.conversation import ConversationService
from app.services.tools import build_registry
from app.services.transcription import TranscriptionService
from app.services.vision import VisionService
from app.storage import build_repositories

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Application:
    """The wired-up bot plus the clients that must be closed on shutdown."""

    bot: Bot
    dispatcher: Dispatcher
    http_client: httpx.AsyncClient
    openai_client: AsyncOpenAI

    async def aclose(self) -> None:
        await self.http_client.aclose()
        await self.openai_client.close()
        await self.bot.session.close()


def build_application(settings: Settings) -> Application:
    """Construct the whole object graph from validated settings."""
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # One shared connection pool for outbound tool traffic.
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    repositories = build_repositories(settings)
    registry = build_registry(http_client)

    agent = AgentService(
        openai_client,
        registry,
        model=settings.openai_model,
        max_iterations=settings.agent_max_iterations,
    )
    conversation = ConversationService(agent, repositories, history_limit=settings.history_limit)

    dispatcher = Dispatcher(
        # Workflow data — aiogram injects these into handlers by parameter name.
        settings=settings,
        repositories=repositories,
        conversation=conversation,
        transcription=TranscriptionService(
            openai_client, model=settings.openai_transcription_model
        ),
        vision=VisionService(openai_client, model=settings.openai_vision_model),
    )
    dispatcher.message.middleware(ThrottlingMiddleware(settings.rate_limit_seconds))
    dispatcher.message.middleware(UserContextMiddleware(repositories))
    dispatcher.include_router(build_router())

    logger.info(
        "application built: storage=%s model=%s tools=%s",
        settings.storage_backend,
        settings.openai_model,
        registry.names,
    )
    return Application(
        bot=bot,
        dispatcher=dispatcher,
        http_client=http_client,
        openai_client=openai_client,
    )
