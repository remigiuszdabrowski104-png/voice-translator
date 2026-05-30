import logging

import deepl

from app.config import get_settings
from app.exceptions import TranslationError

logger = logging.getLogger(__name__)


class TranslationService:
    """Wrapper around the DeepL translation API.

    Attributes:
        _client: The configured deepl.Translator instance.
    """

    def __init__(self) -> None:
        """Initialize the DeepL translator client from application settings."""
        settings = get_settings()
        kwargs = {"auth_key": settings.DEEPL_API_KEY}
        if settings.DEEPL_FREE_API:
            kwargs["server_url"] = "https://api-free.deepl.com"
        self._client = deepl.Translator(**kwargs)

    def translate(self, text: str, target_lang: str = "EN-US") -> str:
        """Translate the given text into the target language.

        Args:
            text: The source text to translate.
            target_lang: The target language code (e.g. "EN-US").

        Returns:
            The translated text as a string.

        Raises:
            TranslationError: If the DeepL API call fails for any reason.
        """
        try:
            result = self._client.translate_text(text, target_lang=target_lang)
            return result.text
        except Exception as exc:
            logger.error("DeepL translation failed: %s", exc, exc_info=True)
            raise TranslationError(f"Translation failed: {exc}") from exc
