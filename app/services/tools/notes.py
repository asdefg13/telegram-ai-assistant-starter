"""Note tools — the assistant's persistent memory, backed by the repository layer."""

from typing import Any

from app.services.tools.base import Tool, ToolContext
from app.storage.models import Note

MAX_NOTE_LENGTH = 2000


class SaveNoteTool(Tool):
    """Persist a fact the user asked the assistant to remember."""

    name = "save_note"
    description = (
        "Save a note for the current user. Call this whenever the user shares "
        "something worth remembering later ('remember that...', preferences, "
        "deadlines, addresses)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The note content, phrased so it makes sense out of context.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional short topic tags, e.g. ['work', 'deadline'].",
            },
        },
        "required": ["text"],
        "additionalProperties": False,
    }

    async def run(self, ctx: ToolContext, **kwargs: Any) -> str:
        text = str(kwargs.get("text", "")).strip()
        if not text:
            return "Error: 'text' is required."
        if len(text) > MAX_NOTE_LENGTH:
            return f"Error: note is too long ({len(text)} chars, max {MAX_NOTE_LENGTH})."

        raw_tags = kwargs.get("tags") or []
        tags = [str(tag).strip().lower() for tag in raw_tags if str(tag).strip()]

        note = await ctx.repositories.notes.add(
            Note(telegram_id=ctx.telegram_id, text=text, tags=tags)
        )
        suffix = f" (tags: {', '.join(note.tags)})" if note.tags else ""
        return f"Saved{suffix}."


class SearchNotesTool(Tool):
    """Recall previously saved notes."""

    name = "search_notes"
    description = (
        "Search the current user's saved notes. Call this before answering any "
        "question about what the user told you earlier."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keyword to look for. Pass an empty string to list recent notes.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "description": "How many notes to return. Defaults to 5.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    async def run(self, ctx: ToolContext, **kwargs: Any) -> str:
        query = str(kwargs.get("query", ""))
        limit = int(kwargs.get("limit", 5))
        limit = max(1, min(limit, 20))

        notes = await ctx.repositories.notes.search(ctx.telegram_id, query, limit=limit)
        if not notes:
            return "No matching notes."

        lines = []
        for note in notes:
            stamp = note.created_at.strftime("%Y-%m-%d")
            tags = f" [{', '.join(note.tags)}]" if note.tags else ""
            lines.append(f"- {stamp}{tags}: {note.text}")
        return "\n".join(lines)
