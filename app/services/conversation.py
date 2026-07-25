"""Conversation service — the seam between transport (aiogram) and the agent.

Handlers stay thin because everything stateful happens here: load history, run
the agent, persist both turns. It is also the easiest thing in the codebase to
unit-test, since it only depends on abstractions.
"""

import logging

from app.services.agent import AgentReply, AgentService
from app.services.tools.base import ToolContext
from app.storage.base import Repositories
from app.storage.models import ChatMessage, MessageKind

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(
        self,
        agent: AgentService,
        repositories: Repositories,
        *,
        history_limit: int = 12,
    ) -> None:
        self._agent = agent
        self._repositories = repositories
        self._history_limit = history_limit

    async def handle(
        self,
        *,
        telegram_id: int,
        text: str,
        kind: MessageKind = "text",
    ) -> AgentReply:
        """Run one user turn end to end and return the agent's reply."""
        history = await self._repositories.messages.recent(telegram_id, limit=self._history_limit)
        reply = await self._agent.reply(
            ctx=ToolContext(telegram_id=telegram_id, repositories=self._repositories),
            prompt=text,
            history=history,
        )

        # Persisted after the call so a failed turn does not poison the history.
        await self._repositories.messages.add(
            ChatMessage(telegram_id=telegram_id, role="user", content=text, kind=kind)
        )
        await self._repositories.messages.add(
            ChatMessage(telegram_id=telegram_id, role="assistant", content=reply.text)
        )

        logger.info("turn complete user=%s kind=%s tools=%s", telegram_id, kind, reply.tool_calls)
        return reply

    async def reset(self, telegram_id: int) -> int:
        """Forget the conversation (notes are kept on purpose)."""
        return await self._repositories.messages.clear(telegram_id)
