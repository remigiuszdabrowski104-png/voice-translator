#!/usr/bin/env python3
"""Download the Piper en_US-lessac-medium voice model from Hugging Face.

This script fetches the .onnx and .onnx.json files for the specified voice
model from the official Piper voices repository and saves them into the
``voices/`` directory. Existing files are skipped.
"""

import logging
from pathlib import Path
from urllib.request import urlretrieve

logger = logging.getLogger(__name__)

VOICE_NAME = "en_US-lessac-medium"
REPO_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
)
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "voices"

FILES: list[str] = [
    f"{VOICE_NAME}.onnx",
    f"{VOICE_NAME}.onnx.json",
]


def download_voice_model() -> None:
    """Download the Piper voice model files if they do not already exist.

    Each file is fetched from the Hugging Face repository and written into
    ``OUTPUT_DIR``. If a file already exists on disk the download is skipped.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for filename in FILES:
        dest = OUTPUT_DIR / filename
        if dest.exists():
            logger.info("Skipping %s (already exists)", dest)
            continue

        url = f"{REPO_URL}/{filename}"
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        logger.info("Downloading %s from %s", filename, url)
        try:
            urlretrieve(url, tmp)
            tmp.rename(dest)
            logger.info("Downloaded %s (%d bytes)", filename, dest.stat().st_size)
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            logger.error("Failed to download %s: %s", filename, exc, exc_info=True)
            raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    download_voice_model()
    logger.info("Voice model download complete.")