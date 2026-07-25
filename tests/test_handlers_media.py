"""Voice and photo handlers."""

from types import SimpleNamespace

from app.handlers.photo import handle_photo
from app.handlers.voice import handle_voice
from app.services.transcription import TranscriptionError
from app.utils.files import MAX_DOWNLOAD_BYTES

from .conftest import TELEGRAM_ID


async def test_voice_is_transcribed_then_answered(
    message, answered, fake_conversation, fake_transcription
):
    message.voice = SimpleNamespace(file_id="voice-1", duration=3)

    await handle_voice(message, fake_conversation, fake_transcription)

    fake_transcription.transcribe.assert_awaited_once_with(b"fake-media-bytes")
    fake_conversation.handle.assert_awaited_once_with(
        telegram_id=TELEGRAM_ID, text="what is the weather in Lisbon", kind="voice"
    )
    # The transcript is echoed first so the user can verify what was heard.
    assert "what is the weather in Lisbon" in answered()[0]
    assert answered()[1] == "Answer from the agent."


async def test_audio_files_take_the_same_path(message, fake_conversation, fake_transcription):
    message.audio = SimpleNamespace(file_id="audio-1", duration=30)

    await handle_voice(message, fake_conversation, fake_transcription)

    message.bot.get_file.assert_awaited_once_with("audio-1")
    fake_conversation.handle.assert_awaited_once()


async def test_silent_recording_does_not_reach_the_agent(
    message, answered, fake_conversation, fake_transcription
):
    message.voice = SimpleNamespace(file_id="voice-1", duration=1)
    fake_transcription.transcribe.side_effect = TranscriptionError("no speech")

    await handle_voice(message, fake_conversation, fake_transcription)

    fake_conversation.handle.assert_not_awaited()
    assert "could not make out any speech" in answered()[0]


async def test_oversized_media_is_rejected_before_download(
    message, answered, fake_conversation, fake_transcription
):
    message.voice = SimpleNamespace(file_id="voice-1", duration=9999)
    message.bot.get_file.return_value = SimpleNamespace(
        file_path="voice/huge.ogg", file_size=MAX_DOWNLOAD_BYTES + 1
    )

    await handle_voice(message, fake_conversation, fake_transcription)

    message.bot.download_file.assert_not_awaited()
    assert "too large" in answered()[0]


async def test_photo_uses_the_largest_size_and_persists_the_exchange(
    message, answered, fake_vision, repositories
):
    message.photo = [
        SimpleNamespace(file_id="thumb", width=90),
        SimpleNamespace(file_id="full", width=1280),
    ]
    message.caption = "how much did I spend?"

    await handle_photo(message, fake_vision, repositories)

    message.bot.get_file.assert_awaited_once_with("full")
    fake_vision.describe.assert_awaited_once()
    assert fake_vision.describe.await_args.kwargs["caption"] == "how much did I spend?"
    assert answered()[0].startswith("A receipt for 42.50 EUR")

    stored = await repositories.messages.recent(TELEGRAM_ID)
    assert [(item.role, item.kind) for item in stored] == [
        ("user", "photo"),
        ("assistant", "text"),
    ]


async def test_photo_without_caption_still_records_a_turn(message, fake_vision, repositories):
    message.photo = [SimpleNamespace(file_id="full", width=1280)]

    await handle_photo(message, fake_vision, repositories)

    stored = await repositories.messages.recent(TELEGRAM_ID)
    assert stored[0].content == "[sent a photo]"


async def test_vision_failure_is_reported_not_raised(message, answered, fake_vision, repositories):
    message.photo = [SimpleNamespace(file_id="full", width=1280)]
    fake_vision.describe.side_effect = RuntimeError("model unavailable")

    await handle_photo(message, fake_vision, repositories)  # must not raise

    assert "could not analyse that image" in answered()[0]
    assert await repositories.messages.recent(TELEGRAM_ID) == []
