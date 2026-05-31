from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DEEPL_API_KEY: str
    DEEPL_FREE_API: bool = True
    GROQ_API_KEY: str = ""
    GROQ_STT_MODEL: str = "whisper-large-v3-turbo"
    GROQ_STT_LANGUAGE: str = "pl"
    STT_MAX_UPLOAD_BYTES: int = 10000000
    VOICE_MODEL_PATH: str = "voices/en_US-lessac-medium.onnx"
    AUDIO_TEMP_DIR: str = "tmp/audio"
    AUDIO_MAX_AGE_SECONDS: int = 86400
    MAX_TEXT_LENGTH: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()