"""API router for translation, audio retrieval, health check, and STT transcription."""

import logging
import re
import uuid
from pathlib import Path

import anyio
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import get_settings
from app.exceptions import STTError, TTSError, TranslationError
from app.models.schemas import TranslateRequest, TranslateResponse, TranscribeResponse
from app.services.stt import STTService
from app.services.translation import TranslationService
from app.services.tts import TTSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

translation_service = TranslationService()
tts_service = TTSService()
stt_service = STTService()
settings = get_settings()


@router.post("/translate", response_model=TranslateResponse, status_code=200)
async def translate(request: TranslateRequest) -> TranslateResponse:
    """Translate text and synthesize audio for the result.

    Args:
        request: The translation request containing source text and target language.

    Returns:
        A TranslateResponse with the translated text and a generated audio_id.

    Raises:
        HTTPException: 503 if translation or TTS synthesis fails.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")

    audio_id = uuid.uuid4().hex
    try:
        translated_text = await anyio.to_thread.run_sync(
            translation_service.translate, request.text, request.target_lang
        )
    except TranslationError as exc:
        logger.error("Translation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        await anyio.to_thread.run_sync(tts_service.synthesize, translated_text, audio_id)
    except TTSError as exc:
        logger.error("TTS error: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TranslateResponse(
        original_text=request.text,
        translated_text=translated_text,
        audio_id=audio_id,
        target_lang=request.target_lang,
    )


@router.get("/audio/{audio_id}")
async def get_audio(audio_id: str) -> FileResponse:
    """Serve a previously synthesized WAV audio file.

    Args:
        audio_id: The unique identifier for the audio file to retrieve.

    Returns:
        A FileResponse streaming the WAV file with media type audio/wav.

    Raises:
        HTTPException: 404 if no audio file exists for the given audio_id.
    """
    if re.fullmatch(r"[A-Za-z0-9_-]+", audio_id) is None:
        raise HTTPException(status_code=400, detail="Invalid audio_id")

    audio_dir = Path(settings.AUDIO_TEMP_DIR).resolve()
    audio_path = audio_dir / f"{audio_id}.wav"
    if not audio_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=f"{audio_id}.wav",
    )


@router.get("/health")
async def health() -> dict:
    """Return the health status of the application and its dependencies.

    Returns:
        A dict with status, deepl availability, and tts availability.
    """
    deepl_status = "available"
    tts_status = "available"

    voice_path = Path(settings.VOICE_MODEL_PATH).resolve()
    if not voice_path.is_file():
        tts_status = "unavailable"

    return {"status": "ok", "deepl": deepl_status, "tts": tts_status}


@router.post("/transcribe", response_model=TranscribeResponse, status_code=200)
async def transcribe(audio: UploadFile = File(...)) -> TranscribeResponse:
    """Transcribe uploaded speech audio to Polish text using Groq Whisper.

    Args:
        audio: The uploaded audio file (multipart form upload).

    Returns:
        A TranscribeResponse containing the transcribed text.

    Raises:
        HTTPException: 400 if the audio file is empty, 413 if it exceeds
            the maximum upload size, 502 if the upstream STT service fails.
    """
    data = await audio.read()

    if not data:
        raise HTTPException(status_code=400, detail="Audio file must not be empty")

    if len(data) > settings.STT_MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds size limit")

    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="Speech-to-text not configured")

    filename = audio.filename if audio.filename else "recording.m4a"

    try:
        text = await anyio.to_thread.run_sync(stt_service.transcribe, data, filename)
    except STTError as exc:
        logger.error("STT error: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="Speech-to-text service unavailable") from exc

    return TranscribeResponse(text=text)