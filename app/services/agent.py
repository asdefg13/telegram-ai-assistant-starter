"""The agent: an OpenAI function-calling loop over the tool registry.

Flow per user message:

1. system prompt + replayed history + the new message go to the model;
2. if the model answers with text, that text is the reply;
3. if it answers with tool calls, each one is dispatched, results are appended
   as ``role="tool"`` messages, and the loop runs again;
4. ``max_iterations`` bounds the loop so a confused model cannot spend budget
   forever.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from app.services.tools.base import ToolContext, ToolRegistry
from app.storage.models import ChatMessage

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a concise, practical Telegram assistant.\n"
    "- Answer in the user's language.\n"
    "- Prefer calling a tool over guessing: check saved notes before claiming you "
    "do not know something, and look up live weather instead of estimating.\n"
    "- Save a note whenever the user shares a durable fact about themselves.\n"
    "- Keep replies under ~120 words unless the user asks for detail. "
    "Telegram renders plain text, so avoid Markdown tables."
)

FALLBACK_REPLY = "I could not produce an answer this time. Try rephrasing?"


@dataclass(slots=True)
class AgentReply:
    """Result of one agent turn."""

    text: str
    tool_calls: list[str] = field(default_factory=list)


class AgentService:
    """Stateless orchestrator — conversation state lives in the repositories."""

    def __init__(
        self,
        client: AsyncOpenAI,
        registry: ToolRegistry,
        *,
        model: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_iterations: int = 5,
        temperature: float = 0.3,
    ) -> None:
        self._client = client
        self._registry = registry
        self._model = model
        self._system_prompt = system_prompt
        self._max_iterations = max_iterations
        self._temperature = temperature

    def _build_messages(self, prompt: str, history: Sequence[ChatMessage]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": self._system_prompt}]
        messages.extend({"role": item.role, "content": item.content} for item in history)
        messages.append({"role": "user", "content": prompt})
        return messages

    async def reply(
        self,
        *,
        ctx: ToolContext,
        prompt: str,
        history: Sequence[ChatMessage] = (),
    ) -> AgentReply:
        """Run one turn of the agent and return the user-facing answer."""
        messages = self._build_messages(prompt, history)
        used_tools: list[str] = []

        for iteration in range(self._max_iterations):
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=self._registry.schemas(),
                temperature=self._temperature,
            )
            choice = response.choices[0].message
            tool_calls = getattr(choice, "tool_calls", None)

            if not tool_calls:
                text = (choice.content or "").strip() or FALLBACK_REPLY
                return AgentReply(text=text, tool_calls=used_tools)

            # Echo the assistant turn back verbatim — the API requires the
            # tool_calls it produced to precede their results.
            messages.append(
                {
                    "role": "assistant",
                    "content": choice.content,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in tool_calls
                    ],
                }
            )

            for call in tool_calls:
                name = call.function.name
                used_tools.append(name)
                logger.info(
                    "iteration=%s user=%s tool=%s args=%s",
                    iteration,
                    ctx.telegram_id,
                    name,
                    call.function.arguments,
                )
                result = await self._registry.dispatch(name, call.function.arguments, ctx)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        logger.warning(
            "agent hit max_iterations=%s for user=%s", self._max_iterations, ctx.telegram_id
        )
        return AgentReply(
            text="That took more steps than I allow myself. Could you narrow the request?",
            tool_calls=used_tools,
        )
