"""Tool abstraction for OpenAI function calling.

A tool declares its own JSON schema and executes against a :class:`ToolContext`,
so adding capability to the agent means adding one class — never touching the
agent loop.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from app.storage.base import Repositories

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ToolContext:
    """Per-request state handed to every tool invocation."""

    telegram_id: int
    repositories: Repositories


class Tool(ABC):
    """Base class for a callable the model may invoke."""

    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[dict[str, Any]]

    @abstractmethod
    async def run(self, ctx: ToolContext, **kwargs: Any) -> str:
        """Execute the tool and return a short, model-readable result."""

    @classmethod
    def schema(cls) -> dict[str, Any]:
        """Return the OpenAI tool definition for this class."""
        return {
            "type": "function",
            "function": {
                "name": cls.name,
                "description": cls.description,
                "parameters": cls.parameters,
            },
        }


class ToolRegistry:
    """Name-to-tool lookup plus safe dispatch.

    Every failure path returns a string rather than raising: the model sees the
    error as a tool result and gets a chance to recover on the next iteration.
    """

    def __init__(self, tools: list[Tool]) -> None:
        self._tools: dict[str, Tool] = {tool.name: tool for tool in tools}

    def __len__(self) -> int:
        return len(self._tools)

    @property
    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        return [type(tool).schema() for tool in self._tools.values()]

    async def dispatch(self, name: str, arguments: str, ctx: ToolContext) -> str:
        tool = self._tools.get(name)
        if tool is None:
            logger.warning("model requested unknown tool %r", name)
            return f"Error: unknown tool {name!r}. Available tools: {', '.join(self.names)}."

        try:
            payload = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError as exc:
            logger.warning("tool %s got malformed arguments: %s", name, exc)
            return f"Error: arguments for {name} were not valid JSON ({exc})."

        if not isinstance(payload, dict):
            return f"Error: arguments for {name} must be a JSON object."

        try:
            return await tool.run(ctx, **payload)
        except TypeError as exc:
            logger.warning("tool %s called with bad signature: %s", name, exc)
            return f"Error: wrong arguments for {name} ({exc})."
        except Exception as exc:  # noqa: BLE001 — never let a tool kill the loop
            logger.exception("tool %s failed", name)
            return f"Error: {name} failed ({type(exc).__name__}: {exc})."
