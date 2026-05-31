# Voice Translator

A lightweight web application for language learning: type Polish text, get an English translation displayed silently as text, and click **Play** to hear it spoken aloud. Designed for discreet use in public places - no automatic audio playback, sound plays only on demand. Keeps a persistent history of your last 5 translations in the browser so you can revisit and replay them throughout the day.

## Features

- **Silent text mode** - translations appear as text only; audio plays exclusively when you click Play, making it safe for public use (shops, libraries, transit)
- **DeepL translation** - high-quality Polish-to-English translations via the DeepL API (free tier supported)
- **Piper TTS** - offline, CPU-only text-to-speech using the Piper speech engine (no GPU required, MIT license)
- **Last-5 history** - your 5 most recent translations persist in browser `localStorage`, surviving page refreshes and browser restarts
- **Play on demand** - each translation and each history entry has its own Play button; audio files live for 24 hours so history playback works all day

## Requirements

- **Python 3.11+**
- A **free DeepL API key** ([sign up here](https://www.deepl.com/pro-api))
- No GPU needed - Piper TTS runs entirely on CPU

## Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd voice-translator

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and set DEEPL_API_KEY=your_key_here

# 4. Download the Piper voice model (~60 MB)
python scripts/download_voice.py
```

## Running

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** in your browser.

## Running Tests

```bash
pytest tests/ -v
```

Run with coverage:

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/translate` | Translate Polish text to English and generate speech audio. Accepts `{"text": "...", "target_lang": "EN-US"}`. Returns `{"original_text", "translated_text", "audio_id", "target_lang"}`. |
| `GET` | `/api/audio/{audio_id}` | Stream the WAV audio file for a given translation. Returns `audio/wav`. |
| `GET` | `/api/health` | Health check. Returns `{"status": "ok", "deepl": "available", "tts": "available"}`. |

## Project Structure

```
voice-translator/
├── app/
│   ├── __init__.py
│   ├── config.py              # Pydantic Settings from .env
│   ├── exceptions.py          # TranslationError, TTSError
│   ├── main.py                # FastAPI app, routing, static files, startup cleanup
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response schemas
│   ├── routers/
│   │   └── translate.py       # POST /api/translate, GET /api/audio, GET /api/health
│   └── services/
│       ├── translation.py     # TranslationService (DeepL)
│       └── tts.py             # TTSService (Piper)
├── frontend/
│   ├── index.html             # Main UI (Polish interface)
│   ├── style.css
│   └── app.js                 # Fetch API calls, localStorage history, Play button logic
├── scripts/
│   └── download_voice.py      # Downloads Piper voice model
├── tests/
│   ├── test_translate.py
│   ├── test_translation_service.py
│   └── test_tts.py
├── voices/                    # Voice model files (downloaded, git-ignored)
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
└── README.md
```

## Notes

- **Microphone / speech-to-text mode** is planned for a future version and is not included in the current release.
- The application is designed to be deployed on a **cheap CPU-only VPS** - no GPU acceleration is needed at any layer.
- Audio files older than 24 hours are automatically cleaned up on server startup.
- Your DeepL API key is stored only in `.env`, which is git-ignored and never committed.
