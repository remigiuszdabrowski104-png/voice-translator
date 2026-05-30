from pydantic import BaseModel, field_validator


class TranslateRequest(BaseModel):
    text: str
    target_lang: str = "EN-US"

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) > 5000:
            raise ValueError("text must not exceed 5000 characters")
        return stripped


class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    audio_id: str
    target_lang: str