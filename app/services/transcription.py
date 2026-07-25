"""Voice transcription through the OpenAI audio API (Whisper)."""

import io
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class TranscriptionError(RuntimeError):
    """Raised when audio could not be turned into text."""


class TranscriptionService:
    """Turn a Telegram voice note into text."""

    def __init__(self, client: AsyncOpenAI, *, model: str = "whisper-1") -> None:
        self._client = client
        self._model = model

    async def transcribe(self, audio: bytes, *, filename: str = "voice.ogg") -> str:
        """Transcribe raw audio bytes.

        Telegram voice notes are OGG/Opus, which the API accepts directly — no
        ffmpeg step needed. The filename matters: the API infers the container
        from the extension.
        """
        if not audio:
            raise TranscriptionError("empty audio payload")

        buffer = io.BytesIO(audio)
        buffer.name = filename

        response = await self._client.audio.transcriptions.create(
            model=self._model,
            file=buffer,
        )
        text = (getattr(response, "text", "") or "").strip()
        if not text:
            raise TranscriptionError("transcription returned no text")

        logger.info("transcribed %s bytes into %s chars", len(audio), len(text))
        return text
