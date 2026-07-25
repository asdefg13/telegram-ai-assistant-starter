"""Tool registry wiring.

Register a new capability by appending one class here — the agent loop and the
handlers stay untouched.
"""

import httpx

from app.services.tools.base import Tool, ToolContext, ToolRegistry
from app.services.tools.notes import SaveNoteTool, SearchNotesTool
from app.services.tools.weather import GetWeatherTool

__all__ = [
    "GetWeatherTool",
    "SaveNoteTool",
    "SearchNotesTool",
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "build_registry",
]


def build_registry(http_client: httpx.AsyncClient | None = None) -> ToolRegistry:
    """Build the default tool set."""
    return ToolRegistry(
        [
            GetWeatherTool(http_client),
            SaveNoteTool(),
            SearchNotesTool(),
        ]
    )
