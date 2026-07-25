"""Shared fixtures.

The suite never touches Telegram, OpenAI or Supabase: transports are mocked and
storage runs on the in-memory repositories, so `pytest` is fast and offline.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.agent import AgentReply, AgentService
from app.services.conversation import ConversationService
from app.services.tools import build_registry
from app.services.tools.base import ToolContext
from app.storage.memory_repo import build_memory_repositories

TELEGRAM_ID = 424242


def make_completion(content: str | None = None, tool_calls: list | None = None):
    """Build a stub that mimics an OpenAI chat completion response."""
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_tool_call(call_id: str, name: str, arguments: str):
    """Build a stub that mimics one tool call inside a completion."""
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


@pytest.fixture
def repositories():
    return build_memory_repositories()


@pytest.fixture
def registry():
    return build_registry()


@pytest.fixture
def tool_context(repositories):
    return ToolContext(telegram_id=TELEGRAM_ID, repositories=repositories)


@pytest.fixture
def openai_client():
    """An AsyncOpenAI-shaped mock; set `.responses` on the queue per test."""
    client = MagicMock()
    client.chat.completions.create = AsyncMock()
    client.audio.transcriptions.create = AsyncMock()
    return client


@pytest.fixture
def agent(openai_client, registry):
    return AgentService(openai_client, registry, model="gpt-4o-mini", max_iterations=3)


@pytest.fixture
def conversation(agent, repositories):
    return ConversationService(agent, repositories, history_limit=4)


@pytest.fixture
def message():
    """A Telegram Message double with async transport methods stubbed out."""
    msg = MagicMock()
    msg.from_user = SimpleNamespace(
        id=TELEGRAM_ID,
        username="client",
        full_name="Test Client",
        language_code="en",
    )
    msg.chat = SimpleNamespace(id=TELEGRAM_ID, type="private")
    msg.text = None
    msg.caption = None
    msg.voice = None
    msg.audio = None
    msg.photo = None
    msg.answer = AsyncMock()
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()
    msg.bot.get_file = AsyncMock(
        return_value=SimpleNamespace(file_path="voice/file_0.ogg", file_size=1024)
    )

    async def _download(file_path, destination):
        destination.write(b"fake-media-bytes")

    msg.bot.download_file = AsyncMock(side_effect=_download)
    return msg


@pytest.fixture
def fake_conversation():
    """A ConversationService double returning a fixed agent reply."""
    service = MagicMock()
    service.handle = AsyncMock(return_value=AgentReply(text="Answer from the agent."))
    service.reset = AsyncMock(return_value=7)
    return service


@pytest.fixture
def fake_transcription():
    service = MagicMock()
    service.transcribe = AsyncMock(return_value="what is the weather in Lisbon")
    return service


@pytest.fixture
def fake_vision():
    service = MagicMock()
    service.describe = AsyncMock(return_value="A receipt for 42.50 EUR from Pingo Doce.")
    return service


@pytest.fixture
def answered(message):
    """Return every text the handler sent back, in order."""

    def _answered() -> list[str]:
        return [call.args[0] for call in message.answer.call_args_list if call.args]

    return _answered
