import logging

from groq import Groq

from app.config import get_settings
from app.exceptions import STTError

logger = logging.getLogger(__name__)


class STTService:
    """Wrapper around the Groq Whisper API for speech-to-text transcription.

    Attributes:
        _api_key: The Groq API key.
        _model: The Whisper model name to use.
        _language: The ISO-639-1 language code for improved accuracy.
    """

    def __init__(self) -> None:
        """Initialize the STT service from application settings."""
        settings = get_settings()
        self._api_key = settings.GROQ_API_KEY
        self._model = settings.GROQ_STT_MODEL
        self._language = settings.GROQ_STT_LANGUAGE
        self._client = Groq(api_key=self._api_key)

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        """Transcribe audio bytes to text using the Groq Whisper API.

        Args:
            audio_bytes: The raw audio file content.
            filename: The filename (including extension) to pass to the API.

        Returns:
            The transcribed text as a string.

        Raises:
            STTError: If the Groq API call fails for any reason.
        """
        if not audio_bytes:
            raise STTError("Audio data must not be empty")

        try:
            transcription = self._client.audio.transcriptions.create(
                file=(filename, audio_bytes),
                model=self._model,
                language=self._language,
                response_format="json",
                temperature=0.0,
            )
            return transcription.text.strip()
        except Exception as exc:
            logger.error("Groq STT transcription failed: %s", exc, exc_info=True)
            raise STTError(f"Speech-to-text transcription failed: {exc}") from exc