"""Integration tests for the STT endpoint: POST /api/transcribe.

The STTService is mocked — no real Groq API calls are made.
Uses FastAPI's TestClient against app.main.app.
"""

import os

os.environ.setdefault("DEEPL_API_KEY", "test-dummy-key-for-tests")
os.environ.setdefault("GROQ_API_KEY", "test-groq-dummy")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.exceptions import STTError  # noqa: E402
from app.main import app  # noqa: E402
import app.routers.translate as translate_mod  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _env_and_cache(monkeypatch: pytest.MonkeyPatch):
    """Ensure required env vars are set and the settings lru_cache is cleared."""
    monkeypatch.setenv("DEEPL_API_KEY", "test-dummy-key-for-tests")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-dummy")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient bound to the FastAPI app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_transcribe_happy_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /api/transcribe with valid audio returns 200 and JSON {text: ...}."""

    def fake_transcribe(audio_bytes: bytes, filename: str) -> str:
        return "To jest transkrypcja."

    monkeypatch.setattr(
        "app.routers.translate.stt_service.transcribe", fake_transcribe
    )

    response = client.post(
        "/api/transcribe",
        files={"audio": ("test.m4a", b"fake-audio-bytes", "audio/mp4")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "To jest transkrypcja."


def test_transcribe_empty_file_returns_400(client: TestClient) -> None:
    """POST /api/transcribe with an empty file returns 400 Bad Request."""
    response = client.post(
        "/api/transcribe",
        files={"audio": ("empty.m4a", b"", "audio/mp4")},
    )

    assert response.status_code == 400


def test_transcribe_oversized_file_returns_413(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /api/transcribe with bytes exceeding STT_MAX_UPLOAD_BYTES returns 413."""
    settings = translate_mod.settings
    max_bytes = settings.STT_MAX_UPLOAD_BYTES

    oversized = b"x" * (max_bytes + 1)

    response = client.post(
        "/api/transcribe",
        files={"audio": ("large.m4a", oversized, "audio/mp4")},
    )

    assert response.status_code == 413


def test_transcribe_stt_error_returns_502(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /api/transcribe returns 502 when stt_service.transcribe raises STTError."""

    def raise_stt_error(audio_bytes: bytes, filename: str) -> str:
        raise STTError("Groq API unavailable")

    monkeypatch.setattr(
        "app.routers.translate.stt_service.transcribe", raise_stt_error
    )

    response = client.post(
        "/api/transcribe",
        files={"audio": ("test.m4a", b"some-audio", "audio/mp4")},
    )

    assert response.status_code == 502


def test_transcribe_missing_api_key_returns_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /api/transcribe returns 503 when GROQ_API_KEY is not configured."""
    monkeypatch.setattr(translate_mod.settings, "GROQ_API_KEY", "")

    response = client.post(
        "/api/transcribe",
        files={"audio": ("test.m4a", b"some-audio", "audio/mp4")},
    )

    assert response.status_code == 503
