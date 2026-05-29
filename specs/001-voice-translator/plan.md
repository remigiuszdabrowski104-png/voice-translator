# Implementation Plan: Voice Translator (v1)

Based on `specs/001-voice-translator/spec.md`.

## Overview

A minimal web app where a user pastes Polish text, clicks one button, receives an English translation from DeepL, and hears it spoken aloud via Piper TTS (CPU-only, offline). Backend is FastAPI + Python; frontend is plain HTML/CSS/JS.

## Architecture Decisions

- Piper TTS runs as a subprocess (piper CLI invoked via subprocess, output piped to a WAV file). No Python bindings needed; easier to swap later.
- Audio stored in tmp/audio/ with unique UUID filenames, cleaned up at startup for files older than AUDIO_MAX_AGE_SECONDS.
- No database. Audio IDs live only in the filesystem; v1 has no persistence requirement.
- Pydantic Settings for config. Single Settings object loaded from .env; no global mutable state.
- Thin routers. All business logic lives in service classes; routers only validate and dispatch.

## Dependency Graph

```
.env / config.py
    |
    +-- services/translation.py  (DeepL wrapper)
    +-- services/tts.py          (Piper wrapper)
    |
    +-- routers/translate.py     (API: POST /api/translate, GET /api/audio, GET /api/health)
            |
            +-- app/main.py      (FastAPI app, static files, startup cleanup)
                    |
                    +-- frontend/ (HTML + CSS + JS - consumes the REST API)

tests/
    +-- conftest.py              (AsyncClient fixtures, mock factories)
    +-- test_translation_service.py
    +-- test_tts.py
    +-- test_translate.py        (endpoint integration tests)
```

## Task List

### Phase 1: Project Skeleton & Config

#### Task 1: Scaffold directory structure, requirements, and config
Description: Create all empty packages, requirements.txt, requirements-dev.txt, .env.example, .gitignore, and app/config.py with Pydantic Settings. No business logic yet - just the skeleton.

Acceptance criteria:
- All directories from the spec exist (app/, app/routers/, app/services/, app/models/, frontend/, tests/, voices/, scripts/, tmp/audio/)
- Every __init__.py is present
- requirements.txt lists: fastapi, uvicorn[standard], deepl, python-dotenv, pydantic-settings; NO GPU dependency
- requirements-dev.txt lists: pytest, pytest-asyncio, httpx
- .env.example contains all variables from section 7 of the spec
- app/config.py exposes a Settings class and a get_settings() function; loads from .env
- python -c "from app.config import get_settings; print(get_settings())" runs without error (with a dummy .env)

Dependencies: None
Estimated scope: S

#### Task 2: Custom exceptions and Pydantic schemas
Description: Define TranslationError and TTSError in app/exceptions.py, and the request/response Pydantic models in app/models/schemas.py.

Acceptance criteria:
- TranslationError and TTSError importable from app.exceptions
- TranslateRequest has text: str (max 5000 chars, non-empty) and target_lang: str = "EN-US"
- TranslateResponse has original_text, translated_text, audio_id, target_lang
- Pydantic validation rejects empty text and text > 5000 chars with a 422

Dependencies: Task 1
Estimated scope: XS

Checkpoint after Tasks 1-2: project installs cleanly; config loads from .env; schemas and exceptions importable.

### Phase 2: Backend Services

#### Task 3: Translation service (DeepL wrapper)
Description: Implement app/services/translation.py - a TranslationService class with translate(text, target_lang) -> str. Raises TranslationError on any DeepL failure.

Acceptance criteria:
- translate returns a non-empty English string (live call verified manually once)
- If DeepL raises any exception, TranslationError is raised instead
- Uses DEEPL_API_KEY and DEEPL_FREE_API from settings
- No print() - uses logging

Dependencies: Tasks 1-2
Estimated scope: S

#### Task 4: TTS service (Piper wrapper)
Description: Implement app/services/tts.py - a TTSService class with synthesize(text, audio_id) -> Path. Invokes piper CLI via subprocess, writes WAV to AUDIO_TEMP_DIR, returns path. Raises TTSError on failure.

Acceptance criteria:
- Returns a Path pointing to an existing .wav file
- Uses VOICE_MODEL_PATH from settings
- Raises TTSError if subprocess exits non-zero or file not created
- No GPU dependency in the invocation command
- No print() - uses logging

Dependencies: Tasks 1-2
Estimated scope: S

Checkpoint after Tasks 3-4: both services importable and unit-testable in isolation.

### Phase 3: API Layer

#### Task 5: Router + FastAPI app + tests
Description: Wire up app/routers/translate.py (three endpoints) and app/main.py (app factory, static files, startup cleanup). Write all tests: conftest.py, test_translate.py, test_translation_service.py, test_tts.py.

Acceptance criteria:
- POST /api/translate happy path returns 200 with translated_text and audio_id
- POST /api/translate empty text returns 400; DeepL error returns 503
- GET /api/audio/{audio_id} existing file returns 200 audio/wav; missing returns 404
- GET /api/health returns {"status": "ok", "deepl": "available", "tts": "available"}
- DeepL and Piper ALWAYS mocked in tests
- pytest tests/ -v all pass
- pytest --cov=app coverage >= 80%
- Startup hook deletes WAV files older than AUDIO_MAX_AGE_SECONDS

Dependencies: Tasks 1-4
Estimated scope: L

Checkpoint after Task 5: pytest all green; coverage >= 80%; all three endpoints respond via curl.

### Phase 4: Frontend

#### Task 6: HTML/CSS/JS frontend
Description: Build frontend/index.html, style.css, app.js. Implements all four UI states from section 6 (initial, loading, success, error). Auto-plays audio on success. "Odtworz ponownie" replays last audio_id without re-translating.

Acceptance criteria:
- Polish UI text matches the table in section 6 exactly
- Translate button disabled during fetch
- On success: translation shown, audio plays automatically, replay button appears
- On error: Polish error message shown, button re-enabled
- Responsive layout works on mobile (375px viewport)
- No external JS/CSS dependencies (no CDN links)
- FastAPI serves frontend/ as static files at /

Dependencies: Task 5
Estimated scope: M

### Phase 5: Documentation & Final Polish

#### Task 7: README and .env.example review
Description: Write README.md with setup instructions, running the server, running tests, required env vars. Verify .env.example complete.

Acceptance criteria:
- README covers prerequisites, install, download voice model, run server, run tests
- .env.example matches section 7 of the spec exactly
- No secrets in any committed file

Dependencies: Tasks 1-6
Estimated scope: XS

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Piper not installable on current Python version | High | download_voice.py checks version; README notes Python 3.11+; fallback: piper-tts PyPI package instead of CLI |
| DeepL free-tier API URL differs from paid | Medium | DEEPL_FREE_API=true switches base URL via deepl.Translator(auth_key, server_url=...) |
| WAV files accumulate in tmp/audio/ | Low | Startup cleanup + AUDIO_MAX_AGE_SECONDS |
| Audio autoplay blocked by browser | Medium | Trigger playback inside the click handler so it counts as user-initiated |
| Piper model file missing at startup | Medium | Health endpoint checks model file existence, reports "tts": "unavailable" |

## Open Questions (resolved)

- /api/health returns 200 with a status field (per spec).
- piper invoked via a configurable PIPER_BINARY env var, defaulting to "piper".

## Recommended implementation order

Task 1 -> Task 2 -> [Task 3 || Task 4] -> Task 5 -> Task 6 -> Task 7

Tasks 3 and 4 (services) are independent and can be implemented in parallel.
