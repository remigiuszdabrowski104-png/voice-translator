"""Integration tests for the API layer: app/routers/translate.py and app/main.py.

All external services (DeepL, Piper TTS) are mocked — no real API calls are made.
Uses FastAPI's TestClient against app.main.app.
"""

# Set a dummy DEEPL_API_KEY in os.environ BEFORE importing any app module,
# so the module-level singletons (TranslationService, TTSService, settings)
# can be instantiated without a real key.
import os
import types

os.environ.setdefault("DEEPL_API_KEY", "test-dummy-key-for-tests")

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.exceptions import TranslationError, TTSError  # noqa: E402
from app.main import app  # noqa: E402
import app.routers.translate as translate_mod  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _env_and_cache(monkeypatch: pytest.MonkeyPatch):
    """Ensure DEEPL_API_KEY is set and the settings lru_cache is cleared
    before and after every test so env changes take effect."""
    monkeypatch.setenv("DEEPL_API_KEY", "test-dummy-key-for-tests")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient bound to the FastAPI app."""
    return TestClient(app)


def _make_fake_settings(audio_temp_dir: str) -> types.SimpleNamespace:
    """Build a SimpleNamespace that mirrors the real settings object but
    with a custom AUDIO_TEMP_DIR — safe to monkeypatch onto the module."""
    real = translate_mod.settings
    return types.SimpleNamespace(
        DEEPL_API_KEY=real.DEEPL_API_KEY,
        DEEPL_FREE_API=real.DEEPL_FREE_API,
        VOICE_MODEL_PATH=real.VOICE_MODEL_PATH,
        AUDIO_TEMP_DIR=audio_temp_dir,
        AUDIO_MAX_AGE_SECONDS=real.AUDIO_MAX_AGE_SECONDS,
        MAX_TEXT_LENGTH=real.MAX_TEXT_LENGTH,
    )


# ---------------------------------------------------------------------------
# Test 1: GET /api/health — should return 200 and {"status": "ok", ...}
# ---------------------------------------------------------------------------


def test_health_returns_ok(client: TestClient) -> None:
    """GET /api/health returns HTTP 200 and a JSON body containing status='ok'."""
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


# ---------------------------------------------------------------------------
# Test 2: POST /api/translate happy path
# ---------------------------------------------------------------------------


def test_translate_happy_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """POST /api/translate with valid input returns 200 and the expected fields."""

    def fake_translate(text: str, target_lang: str) -> str:
        return "Hello"

    def fake_synthesize(text: str, audio_id: str) -> Path:
        out = tmp_path / f"{audio_id}.wav"
        out.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
        return out

    monkeypatch.setattr(
        "app.routers.translate.translation_service.translate", fake_translate
    )
    monkeypatch.setattr(
        "app.routers.translate.tts_service.synthesize", fake_synthesize
    )

    response = client.post(
        "/api/translate",
        json={"text": "Hola", "target_lang": "EN-US"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["original_text"] == "Hola"
    assert body["translated_text"] == "Hello"
    assert body["audio_id"]  # non-empty string
    assert body["target_lang"] == "EN-US"


# ---------------------------------------------------------------------------
# Test 3: POST /api/translate with empty/whitespace text → 400
# ---------------------------------------------------------------------------


def test_translate_empty_text_returns_400(client: TestClient) -> None:
    """POST /api/translate with whitespace-only text returns 400 Bad Request.

    The Pydantic validator strips the text; the router then rejects the
    resulting empty string with a 400 HTTPException.
    """
    response = client.post(
        "/api/translate",
        json={"text": "   ", "target_lang": "EN-US"},
    )

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test 4: POST /api/translate with text > 5000 chars → 422
# ---------------------------------------------------------------------------


def test_translate_text_too_long_returns_422(client: TestClient) -> None:
    """POST /api/translate with text exceeding 5000 characters returns 422.

    The Pydantic field_validator raises ValueError for text longer than
    5000 characters after stripping, which FastAPI converts to 422.
    """
    response = client.post(
        "/api/translate",
        json={"text": "a" * 5001, "target_lang": "EN-US"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 5: POST /api/translate — TranslationError → 503
# ---------------------------------------------------------------------------


def test_translate_translation_error_returns_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /api/translate returns 503 when translation_service.translate
    raises TranslationError."""

    def raise_translation_error(text: str, target_lang: str) -> str:
        raise TranslationError("DeepL unavailable")

    monkeypatch.setattr(
        "app.routers.translate.translation_service.translate",
        raise_translation_error,
    )

    response = client.post(
        "/api/translate",
        json={"text": "Hello world", "target_lang": "EN-US"},
    )

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Test 6: POST /api/translate — TTSError → 503
# ---------------------------------------------------------------------------


def test_translate_tts_error_returns_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /api/translate returns 503 when tts_service.synthesize raises TTSError."""

    monkeypatch.setattr(
        "app.routers.translate.translation_service.translate",
        lambda text, target_lang: "Hello",
    )

    def raise_tts_error(text: str, audio_id: str) -> Path:
        raise TTSError("Piper not found")

    monkeypatch.setattr(
        "app.routers.translate.tts_service.synthesize",
        raise_tts_error,
    )

    response = client.post(
        "/api/translate",
        json={"text": "Hello world", "target_lang": "EN-US"},
    )

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Test 7: GET /api/audio/{id} with illegal id → 400
# ---------------------------------------------------------------------------


def test_audio_illegal_id_returns_400(client: TestClient) -> None:
    """GET /api/audio/{id} returns 400 when the id contains characters
    outside [A-Za-z0-9_-] (i.e. fails the router regex guard).

    The '!' character is a valid URL path character that passes through
    the TestClient unmodified, so FastAPI receives it and the regex guard
    rejects it with a 400.
    """
    # '!' is not in [A-Za-z0-9_-], so the regex guard triggers → 400
    response = client.get("/api/audio/foo!bar")

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test 8: GET /api/audio/{id} — well-formed but nonexistent id → 404
# ---------------------------------------------------------------------------


def test_audio_nonexistent_id_returns_404(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """GET /api/audio/{id} returns 404 for a valid id with no corresponding file."""
    # Point AUDIO_TEMP_DIR at a known empty temp directory
    monkeypatch.setattr(
        translate_mod, "settings", _make_fake_settings(str(tmp_path))
    )

    response = client.get("/api/audio/nonexistent123")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test 9: GET /api/audio/{id} — file exists → 200 with audio/wav content-type
# ---------------------------------------------------------------------------


def test_audio_serves_existing_file(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """GET /api/audio/{id} returns 200 and audio/wav content-type when the
    corresponding .wav file exists in AUDIO_TEMP_DIR."""
    audio_id = "test-audio-abc123"
    wav_file = tmp_path / f"{audio_id}.wav"
    wav_file.write_bytes(b"RIFF\x04\x00\x00\x00WAVE")  # minimal valid WAV header

    # Redirect the module-level settings to use our temp directory
    monkeypatch.setattr(
        translate_mod, "settings", _make_fake_settings(str(tmp_path))
    )

    response = client.get(f"/api/audio/{audio_id}")

    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "audio/wav" in content_type
