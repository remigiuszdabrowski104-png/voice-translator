"""Tests for app.services.stt.STTService.

All Groq API calls are mocked — no real HTTP requests are made.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.config import get_settings
from app.exceptions import STTError
from app.services.stt import STTService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _set_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure required env vars are set so get_settings() doesn't fail."""
    monkeypatch.setenv("DEEPL_API_KEY", "test-fake-key-12345")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key-67890")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Clear the lru_cache on get_settings() before each test."""
    get_settings.cache_clear()


@pytest.fixture
def mock_groq_client() -> MagicMock:
    """Patch the Groq class inside app.services.stt to avoid real API calls."""
    patcher = patch("app.services.stt.Groq", autospec=True)
    mock_cls = patcher.start()
    mock_instance = MagicMock()
    mock_cls.return_value = mock_instance
    yield mock_instance
    patcher.stop()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSTTService:
    """Suite for STTService.transcribe()."""

    def test_transcribe_returns_text_on_success(
        self, mock_groq_client: MagicMock
    ) -> None:
        """transcribe() returns the stripped .text from the transcription result."""
        fake_transcription = MagicMock()
        fake_transcription.text = "  To jest test.  "
        mock_groq_client.audio.transcriptions.create.return_value = fake_transcription

        service = STTService()

        result = service.transcribe(b"fake-audio-data", "test.m4a")

        assert result == "To jest test."
        mock_groq_client.audio.transcriptions.create.assert_called_once_with(
            file=("test.m4a", b"fake-audio-data"),
            model="whisper-large-v3-turbo",
            language="pl",
            response_format="json",
            temperature=0.0,
        )

    def test_transcribe_raises_stt_error_on_groq_exception(
        self, mock_groq_client: MagicMock
    ) -> None:
        """transcribe() wraps any Groq exception in an STTError."""
        mock_groq_client.audio.transcriptions.create.side_effect = RuntimeError(
            "network error"
        )

        service = STTService()

        with pytest.raises(
            STTError, match="Speech-to-text transcription failed: network error"
        ):
            service.transcribe(b"fake-audio-data", "test.m4a")

    def test_transcribe_raises_on_empty_audio_bytes(self) -> None:
        """transcribe() raises STTError when audio_bytes is empty."""
        service = STTService()

        with pytest.raises(STTError, match="Audio data must not be empty"):
            service.transcribe(b"", "test.m4a")