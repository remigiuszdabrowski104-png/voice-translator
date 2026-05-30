"""FastAPI application factory for the voice-translator service."""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers.translate import router as translate_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


def _cleanup_old_audio_files() -> None:
    """Delete WAV files in AUDIO_TEMP_DIR older than AUDIO_MAX_AGE_SECONDS."""
    audio_dir = Path(settings.AUDIO_TEMP_DIR)
    if not audio_dir.is_dir():
        return

    max_age = settings.AUDIO_MAX_AGE_SECONDS
    now = time.time()
    deleted = 0

    for filepath in audio_dir.iterdir():
        if filepath.suffix != ".wav":
            continue
        age = now - filepath.stat().st_mtime
        if age > max_age:
            filepath.unlink()
            deleted += 1
            logger.info(
                "Deleted aged audio file: %s (age=%.0fs, max=%ds)",
                filepath.name, age, max_age,
            )

    if deleted:
        logger.info("Startup cleanup: removed %d expired WAV file(s)", deleted)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: run startup tasks before serving requests."""
    _cleanup_old_audio_files()
    yield


app = FastAPI(title="Voice Translator", lifespan=lifespan)

app.include_router(translate_router)


frontend_dir = Path("frontend").resolve()
if frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")