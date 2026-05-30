"""Tests for app.services.tts.TTSService.

All subprocess calls are mocked — no real Piper TTS is invoked.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import get_settings
from app.exceptions import TTSError
from app.services.tts import TTSService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _set_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure required env vars are set so get_settings() doesn't fail."""
    monkeypatch.setenv("DEEPL_API_KEY", "test-fake-key-12345")
    monkeypatch.setenv("VOICE_MODEL_PATH", "voices/test-model.onnx")
    monkeypatch.setenv("AUDIO_TEMP_DIR", "tmp/audio")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Clear the lru_cache on get_settings() before each test.

    Without this, a test that changes env vars would still see the
    previously cached Settings object.
    """
    get_settings.cache_clear()


@pytest.fixture
def mock_subprocess_run() -> MagicMock:
    """Patch subprocess.run inside app.services.tts to avoid real Piper."""
    with patch("app.services.tts.subprocess.run") as mock_run:
        yield mock_run


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTTSService:
    """Suite for TTSService.synthesize()."""

    def test_synthesize_returns_path_on_success(
        self,
        mock_subprocess_run: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """synthesize() returns the expected Path when Piper succeeds
        and the output WAV file is created on disk."""
        # Arrange
        audio_id = "test-audio-123"
        output_dir = tmp_path / "audio_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        expected_path = output_dir / f"{audio_id}.wav"
        expected_path.write_text("fake wav content")  # simulate real file

        monkeypatch.setenv("AUDIO_TEMP_DIR", str(output_dir))

        mock_subprocess_run.return_value = MagicMock(
            returncode=0, stderr=""
        )

        service = TTSService()

        # Act
        result = service.synthesize("Hello world", audio_id)

        # Assert
        assert result == expected_path
        assert result.exists()
        assert result.stat().st_size > 0
        mock_subprocess_run.assert_called_once()

    def test_synthesize_raises_on_nonzero_returncode(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        """synthesize() raises TTSError when Piper exits with non-zero code."""
        # Arrange
        mock_subprocess_run.return_value = MagicMock(
            returncode=1, stderr="model not found"
        )

        service = TTSService()

        # Act / Assert
        with pytest.raises(TTSError, match="Piper exited with code 1"):
            service.synthesize("Hello world", "test-audio-ok")

    def test_synthesize_raises_when_output_file_missing(
        self,
        mock_subprocess_run: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """synthesize() raises TTSError when Piper returns 0 but the
        expected WAV file does not exist on disk."""
        # Arrange
        audio_id = "test-audio-missing"
        output_dir = tmp_path / "audio_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("AUDIO_TEMP_DIR", str(output_dir))

        mock_subprocess_run.return_value = MagicMock(
            returncode=0, stderr=""
        )
        # Intentionally NOT creating the output file

        service = TTSService()

        # Act / Assert
        with pytest.raises(
            TTSError, match="Piper did not produce output file"
        ):
            service.synthesize("Hello world", audio_id)

    @pytest.mark.parametrize(
        "bad_audio_id",
        [
            "../etc",
            "../../secret",
            "foo/bar",
            "a<b>",
            ".hidden",
        ],
    )
    def test_synthesize_raises_value_error_for_illegal_chars(
        self, bad_audio_id: str
    ) -> None:
        """synthesize() raises ValueError when audio_id contains
        characters that could enable path traversal or shell injection."""
        # Arrange
        service = TTSService()

        # Act / Assert
        with pytest.raises(ValueError, match="illegal characters"):
            service.synthesize("Hello world", bad_audio_id)
