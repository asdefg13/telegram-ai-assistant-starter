"""Image understanding.

Photos are sent inline as base64 data URLs, which keeps the bot stateless — no
public bucket, no signed URLs, nothing to clean up afterwards.
"""

import base64
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = (
    "Describe this image for a user who cannot see it. If it contains text, a "
    "receipt, a document or a screenshot, extract the important values. Be brief."
)


class VisionService:
    """Answer questions about an image."""

    def __init__(self, client: AsyncOpenAI, *, model: str = "gpt-4o-mini") -> None:
        self._client = client
        self._model = model

    async def describe(
        self,
        image: bytes,
        *,
        caption: str | None = None,
        mime_type: str = "image/jpeg",
        max_tokens: int = 600,
    ) -> str:
        """Return the model's answer about ``image``, guided by an optional caption."""
        data_url = f"data:{mime_type};base64,{base64.b64encode(image).decode()}"
        instruction = (caption or "").strip() or DEFAULT_PROMPT

        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        logger.info("described %s bytes of image data", len(image))
        return text or "I could not read anything useful from that image."
