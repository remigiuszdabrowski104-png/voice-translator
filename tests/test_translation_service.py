"""Tests for app.services.translation.TranslationService.

All DeepL API calls are mocked — no real HTTP requests are made.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.config import get_settings
from app.exceptions import TranslationError
from app.services.translation import TranslationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _set_deepl_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a DEEPL_API_KEY is available so get_settings() doesn't fail."""
    monkeypatch.setenv("DEEPL_API_KEY", "test-fake-key-12345")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Clear the lru_cache on get_settings() before each test.

    Without this, a test that changes DEEPL_FREE_API would still see the
    previously cached Settings object.
    """
    get_settings.cache_clear()


@pytest.fixture
def mock_deepl_translator() -> MagicMock:
    """Patch every new deepl.Translator instance with a MagicMock."""
    patcher = patch("app.services.translation.deepl.Translator", autospec=True)
    mock_cls = patcher.start()
    mock_instance = MagicMock()
    mock_cls.return_value = mock_instance
    yield mock_instance
    patcher.stop()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTranslationService:
    """Suite for TranslationService.translate()."""

    def test_translate_returns_text_on_success(
        self, mock_deepl_translator: MagicMock
    ) -> None:
        """translate() returns the .text attribute of the DeepL result object."""
        # Arrange
        fake_result = MagicMock()
        fake_result.text = "Hola, mundo"
        mock_deepl_translator.translate_text.return_value = fake_result

        service = TranslationService()

        # Act
        result = service.translate("Hello, world", target_lang="ES")

        # Assert
        assert result == "Hola, mundo"
        mock_deepl_translator.translate_text.assert_called_once_with(
            "Hello, world", target_lang="ES"
        )

    def test_translate_raises_translation_error_on_deepl_exception(
        self, mock_deepl_translator: MagicMock
    ) -> None:
        """translate() wraps any DeepL exception in a TranslationError."""
        # Arrange
        mock_deepl_translator.translate_text.side_effect = RuntimeError(
            "connection timeout"
        )

        service = TranslationService()

        # Act / Assert
        with pytest.raises(TranslationError, match="Translation failed: connection timeout"):
            service.translate("Hello", target_lang="DE")

    def test_free_api_server_url_when_deepl_free_api_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """deepl.Translator receives server_url when DEEPL_FREE_API is true."""
        monkeypatch.setenv("DEEPL_FREE_API", "true")

        with patch("app.services.translation.deepl.Translator") as mock_cls:
            mock_cls.return_value = MagicMock()

            TranslationService()

            mock_cls.assert_called_once_with(
                auth_key="test-fake-key-12345",
                server_url="https://api-free.deepl.com",
            )

    def test_no_server_url_when_deepl_free_api_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """deepl.Translator does NOT receive server_url when DEEPL_FREE_API is false."""
        monkeypatch.setenv("DEEPL_FREE_API", "false")

        with patch("app.services.translation.deepl.Translator") as mock_cls:
            mock_cls.return_value = MagicMock()

            TranslationService()

            # Only auth_key should be passed — no server_url
            mock_cls.assert_called_once_with(auth_key="test-fake-key-12345")