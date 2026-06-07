# Voice Translator

A lightweight web application for language learning: type Polish text, get an English translation displayed silently as text, and click **Play** to hear it spoken aloud. Designed for discreet use in public places - no automatic audio playback, sound plays only on demand. Keeps a persistent history of your last 5 translations in the browser so you can revisit and replay them throughout the day.

## Features

- **Silent text mode** - translations appear as text only; audio plays exclusively when you click Play, making it safe for public use (shops, libraries, transit)
- **DeepL translation** - high-quality Polish-to-English translations via the DeepL API (free tier supported)
- **Piper TTS** - offline, CPU-only text-to-speech using the Piper speech engine (no GPU required, MIT license)
- **Voice input (speech-to-text)** - speak instead of typing; your speech is transcribed to Polish via Groq Whisper, then translated. Type or talk, whichever you prefer.
- **Last-5 history** - your 5 most recent translations persist in browser `localStorage`, surviving page refreshes and browser restarts
- **Play on demand** - each translation and each history entry has its own Play button; audio files live for 24 hours so history playback works all day

## Requirements

- **Python 3.11+**
- A **free DeepL API key** ([sign up here](https://www.deepl.com/pro-api))
- A **free Groq API key** ([sign up here](https://console.groq.com)) for voice input - no credit card needed
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
| `POST` | `/api/transcribe` | Transcribe uploaded speech audio to Polish text via Groq Whisper. Accepts an audio file upload. Returns `{"text": "..."}`. |
| `GET` | `/api/health` | Health check. Returns `{"status": "ok", "deepl": "available", "tts": "available"}`. |

## Project Structure

```
voice-translator/
â”śâ”€â”€ app/
â”‚   â”śâ”€â”€ __init__.py
â”‚   â”śâ”€â”€ config.py              # Pydantic Settings from .env
â”‚   â”śâ”€â”€ exceptions.py          # TranslationError, TTSError
â”‚   â”śâ”€â”€ main.py                # FastAPI app, routing, static files, startup cleanup
â”‚   â”śâ”€â”€ models/
â”‚   â”‚   â””â”€â”€ schemas.py         # Pydantic request/response schemas
â”‚   â”śâ”€â”€ routers/
â”‚   â”‚   â””â”€â”€ translate.py       # POST /api/translate, GET /api/audio, GET /api/health
â”‚   â””â”€â”€ services/
â”‚       â”śâ”€â”€ translation.py     # TranslationService (DeepL)
â”‚       â””â”€â”€ tts.py             # TTSService (Piper)
â”śâ”€â”€ frontend/
â”‚   â”śâ”€â”€ index.html             # Main UI (Polish interface)
â”‚   â”śâ”€â”€ style.css
â”‚   â””â”€â”€ app.js                 # Fetch API calls, localStorage history, Play button logic
â”śâ”€â”€ scripts/
â”‚   â””â”€â”€ download_voice.py      # Downloads Piper voice model
â”śâ”€â”€ tests/
â”‚   â”śâ”€â”€ test_translate.py
â”‚   â”śâ”€â”€ test_translation_service.py
â”‚   â””â”€â”€ test_tts.py
â”śâ”€â”€ voices/                    # Voice model files (downloaded, git-ignored)
â”śâ”€â”€ .env.example
â”śâ”€â”€ requirements.txt
â”śâ”€â”€ requirements-dev.txt
â”śâ”€â”€ .gitignore
â””â”€â”€ README.md
```

## Notes

- The application is designed to be deployed on a **cheap CPU-only VPS** - no GPU acceleration is needed at any layer.
- Audio files older than 24 hours are automatically cleaned up on server startup.
- Your DeepL API key is stored only in `.env`, which is git-ignored and never committed.
