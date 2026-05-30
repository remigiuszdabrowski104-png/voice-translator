class AppError(Exception):
    """Base exception class for application-level errors."""


class TranslationError(AppError):
    """Raised when a translation operation fails."""


class TTSError(AppError):
    """Raised when a text-to-speech synthesis operation fails."""