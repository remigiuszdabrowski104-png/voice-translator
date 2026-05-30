import logging
import re
import subprocess
import sys
from pathlib import Path

from app.config import get_settings
from app.exceptions import TTSError

logger = logging.getLogger(__name__)


class TTSService:
    """Wraps the Piper TTS CLI for text-to-speech synthesis.

    Attributes:
        _piper_cmd: The piper invocation command (e.g. [sys.executable, '-m', 'piper']).
        _model_path: Path to the Piper voice model (.onnx).
        _output_dir: Directory where synthesized WAV files are written.
    """

    def __init__(self, piper_cmd: list[str] | None = None) -> None:
        """Initialize the TTS service.

        Args:
            piper_cmd: Override for the piper CLI invocation. Defaults to
                [sys.executable, '-m', 'piper'].
        """
        settings = get_settings()
        self._piper_cmd = piper_cmd if piper_cmd is not None else [sys.executable, "-m", "piper"]
        self._model_path = Path(settings.VOICE_MODEL_PATH).resolve()
        self._output_dir = Path(settings.AUDIO_TEMP_DIR).resolve()

    def synthesize(self, text: str, audio_id: str) -> Path:
        """Convert text to speech and write the result as a WAV file.

        Args:
            text: The text to synthesize into speech.
            audio_id: Unique identifier used as the output filename stem.

        Returns:
            A Path pointing to the synthesized WAV file.

        Raises:
            TTSError: If the subprocess exits with a non-zero code or the
                output file was not created.
        """
        if not re.fullmatch(r"[A-Za-z0-9_-]+", audio_id):
            raise ValueError(f"audio_id contains illegal characters: {audio_id!r}")

        self._output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._output_dir / f"{audio_id}.wav"

        cmd = [
            *self._piper_cmd,
            "-m", str(self._model_path),
            "-f", str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                timeout=60,
            )
        except FileNotFoundError as exc:
            logger.error(
                "Piper executable not found: %s %s",
                self._piper_cmd, exc, exc_info=True,
            )
            raise TTSError(
                f"Piper executable not found: {' '.join(self._piper_cmd)}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            logger.error("Piper synthesis timed out for audio_id=%s", audio_id, exc_info=True)
            raise TTSError(f"Piper synthesis timed out for audio_id={audio_id}") from exc
        except Exception as exc:
            logger.error(
                "Piper synthesis failed for audio_id=%s: %s",
                audio_id, exc, exc_info=True,
            )
            raise TTSError(f"Piper synthesis failed for audio_id={audio_id}: {exc}") from exc

        if result.returncode != 0:
            logger.error(
                "Piper exited with code %d for audio_id=%s: %s",
                result.returncode, audio_id, result.stderr.strip(),
            )
            raise TTSError(
                f"Piper exited with code {result.returncode} for audio_id={audio_id}: "
                f"{result.stderr.strip()}"
            )

        if not output_path.exists():
            logger.error(
                "Piper did not produce output file for audio_id=%s: expected %s",
                audio_id, output_path,
            )
            raise TTSError(
                f"Piper did not produce output file for audio_id={audio_id}: "
                f"expected {output_path}"
            )

        size = output_path.stat().st_size
        logger.info("Synthesized audio_id=%s to %s (%d bytes)", audio_id, output_path, size)
        return output_path