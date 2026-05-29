# Specyfikacja: Aplikacja do nauki jezykow przez tlumaczenie z odsluchem

- **Wersja:** 1.0
- **Data:** 2026-05-30
- **Branch:** 001-voice-translator
- **Jezyk interfejsu:** Polski
- **Jezyk kodu:** Angielski (nazwy zmiennych, funkcji, komentarze)

---

## 1. Cel projektu

Minimalna, dzialajaca aplikacja webowa, ktora pozwala uzytkownikowi:

- Wpisac lub wkleic tekst po polsku
- Kliknac jeden przycisk, by otrzymac tlumaczenie na angielski i uslyszec je na glos
- Odtworzyc tlumaczenie ponownie bez kolejnego tlumaczenia

**Uzytkownik:** osoba uczaca sie angielskiego, korzysta z przegladarki na telefonie lub komputerze.

**Kryterium sukcesu v1:** Uzytkownik wkleja zdanie po polsku, klika "Tlumacz i odtworz", widzi angielskie tlumaczenie i slyszy je przez glosnik w ciagu kilku sekund od klikniecia.

---

## 2. Stos technologiczny

| Warstwa | Technologia |
|---|---|
| Backend | Python 3.11+ + FastAPI |
| Tlumaczenie | DeepL API (REST), biblioteka deepl-python |
| Synteza mowy | Piper TTS (CPU-only, offline, licencja MIT) |
| Serwowanie statyki | FastAPI StaticFiles |
| Frontend | HTML5 + CSS3 + Vanilla JS (bez frameworka) |
| Testy | pytest + pytest-asyncio + httpx AsyncClient |
| Zaleznosci | pip + requirements.txt |
| Konfiguracja | python-dotenv + .env |

**Ograniczenie krytyczne:** Zero zaleznosci od GPU. Zadnych bibliotek wymagajacych CUDA. Piper dziala wylacznie na CPU.

**Uwaga o Pythonie:** docelowo Python 3.11+. Jesli Piper nie zainstaluje sie na zainstalowanej wersji Pythona, jest to dopuszczalny punkt do rozwiazania w fazie planu (np. wskazanie kompatybilnej wersji lub alternatywnego silnika TTS).

---

## 3. Komendy

```
# Instalacja zaleznosci
pip install -r requirements.txt

# Uruchomienie serwera deweloperskiego
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Uruchomienie testow
pytest tests/ -v

# Uruchomienie testow z pokryciem
pytest tests/ -v --cov=app --cov-report=term-missing

# Pobranie modelu glosowego Piper (jednorazowo)
python scripts/download_voice.py
```

---

## 4. Struktura projektu

```
voice-translator/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, routing, startup
│   ├── config.py            # Settings (pydantic-settings), env vars
│   ├── exceptions.py        # Custom exceptions (TranslationError, TTSError)
│   ├── routers/
│   │   ├── __init__.py
│   │   └── translate.py     # POST /api/translate, GET /api/audio/{id}, GET /api/health
│   ├── services/
│   │   ├── __init__.py
│   │   ├── translation.py   # DeepL API client wrapper
│   │   └── tts.py           # Piper TTS wrapper
│   └── models/
│       ├── __init__.py
│       └── schemas.py       # Pydantic request/response models
├── frontend/
│   ├── index.html           # Glowna strona aplikacji (UI po polsku)
│   ├── style.css
│   └── app.js
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_translate.py
│   ├── test_tts.py
│   └── test_translation_service.py
├── voices/
│   └── .gitkeep
├── scripts/
│   └── download_voice.py
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
└── README.md
```

---

## 5. Specyfikacja API

### POST /api/translate

Zadanie:
```
{
  "text": "Dzien dobry, jak sie masz?",
  "target_lang": "EN-US"
}
```

Odpowiedz (200 OK):
```
{
  "original_text": "Dzien dobry, jak sie masz?",
  "translated_text": "Good morning, how are you?",
  "audio_id": "a1b2c3d4",
  "target_lang": "EN-US"
}
```

Bledy:
- 400 - pusty tekst lub brak pola text
- 422 - blad walidacji Pydantic
- 503 - blad zewnetrznego API (DeepL niedostepny)
- 500 - blad wewnetrzny

Logika:
1. Walidacja wejscia (nie pusty, max 5000 znakow)
2. Tlumaczenie przez DeepL (PL -> EN-US)
3. Synteza mowy przetlumaczonego tekstu przez Piper -> plik WAV
4. Zapis pliku audio do katalogu tymczasowego z unikalnym audio_id
5. Zwrot JSON z audio_id

### GET /api/audio/{audio_id}

Odpowiedz (200 OK): plik audio (audio/wav), naglowek Content-Type ustawiony poprawnie.

Bledy:
- 404 - audio_id nie istnieje lub wygasl

Logika: Serwuje plik z katalogu tymczasowego. Pliki starsze niz 1 godzina moga byc usuwane (proste czyszczenie przy starcie).

### GET /api/health

Odpowiedz:
```
{
  "status": "ok",
  "deepl": "available",
  "tts": "available"
}
```

Uzywany do monitorowania i testow integracyjnych.

---

## 6. Interfejs uzytkownika (Polski)

Jeden ekran, responsywny (dziala na telefonie).

Stany UI:
- **Poczatkowy:** textarea i przycisk "Tlumacz i odtworz" aktywny
- **Ladowanie:** przycisk nieaktywny, tekst "Tlumacze...", spinner
- **Sukces:** wyswietlone tlumaczenie, przycisk "Odtworz ponownie" widoczny, audio odtwarzane automatycznie
- **Blad:** komunikat po polsku

Teksty interfejsu (po polsku):

| Element | Tekst |
|---|---|
| Tytul strony | Tlumacz i ucz sie |
| Naglowek | Tlumacz i ucz sie angielskiego |
| Placeholder textarea | Wpisz lub wklej tekst po polsku... |
| Przycisk glowny | Tlumacz i odtworz |
| Przycisk glowny (ladowanie) | Tlumacze... |
| Naglowek sekcji wyniku | Tlumaczenie |
| Przycisk ponownego odtworzenia | Odtworz ponownie |
| Blad ogolny | Wystapil blad. Sprobuj ponownie. |
| Blad pustego pola | Wpisz tekst przed tlumaczeniem. |
| Blad zbyt dlugiego tekstu | Tekst jest zbyt dlugi (max 5000 znakow). |

---

## 7. Konfiguracja (zmienne srodowiskowe)

Plik `.env.example`:
```
# Wymagane
DEEPL_API_KEY=your_deepl_api_key_here

# Opcjonalne
DEEPL_FREE_API=true
VOICE_MODEL_PATH=voices/en_US-lessac-medium.onnx
AUDIO_TEMP_DIR=tmp/audio
AUDIO_MAX_AGE_SECONDS=3600
MAX_TEXT_LENGTH=5000
```

---

## 8. Styl kodu

- Docstringi po angielsku, styl Google
- Typowanie statyczne wszedzie
- Wyjatki wlasne w app/exceptions.py (TranslationError, TTSError)
- Serwisy jako klasy z metodami
- Routery cienkie - logika biznesowa wylacznie w serwisach
- Brak print() - logowanie przez modul logging
- Linie max 100 znakow

---

## 9. Strategia testowania

Framework: pytest + pytest-asyncio + httpx AsyncClient

| Poziom | Co testujemy | Gdzie |
|---|---|---|
| Jednostkowe | Serwisy (translation, tts) z mockami | tests/test_*_service.py |
| Integracyjne | Endpointy FastAPI z mockami zewnetrznych API | tests/test_*.py |
| Brak w v1 | E2E, testy frontendu | - |

Zasady:
- Zewnetrzne API (DeepL) ZAWSZE mockowane w testach - nie wolno odpytywac prawdziwego API
- Piper TTS mockowany - testy generuja falszywy plik WAV
- Kazdy endpoint ma test dla sciezki szczesliwej i glownych bledow (400, 503)
- Pokrycie: minimum 80% dla kodu w app/

---

## 10. Projekt pod przyszle rozszerzenia (NIE budowac w v1)

| Przyszla funkcja | Jak v1 to umozliwia |
|---|---|
| Tryb mikrofonu (STT) | Nowy router POST /api/transcribe -> istniejacy pipeline tlumaczenia |
| Wiele jezykow docelowych | Pole target_lang juz jest w API; UI dostanie <select> |
| PWA (instalowalna na telefonie) | Statyczny frontend -> dodac manifest.json + service-worker.js |
| VPS bez GPU | Piper CPU-only juz teraz; Docker Compose z jednym serwisem |

---

## 11. Granice (Boundaries)

**Zawsze:**
- Uruchom pytest przed zgloszeniem zmiany
- Waliduj dane wejsciowe na poziomie Pydantic przed przekazaniem do serwisow
- Loguj bledy zewnetrznych API z pelnym traceback
- Trzymaj klucz API wylacznie w .env, nigdy w kodzie

**Zapytaj najpierw:**
- Zmiana silnika TTS (zastapienie Piper innym)
- Dodanie bazy danych (historia tlumaczen)
- Zmiana domyslnego jezyka docelowego
- Dodanie uwierzytelniania

**Nigdy:**
- Nie commituj .env z prawdziwym kluczem API
- Nie dodawaj zaleznosci wymagajacych GPU (torch z CUDA, etc.)
- Nie usuwaj testow zamiast naprawiac kod
- Nie odpytuj DeepL API w testach automatycznych

---

## 12. Kryteria sukcesu (testowalne)

- [ ] pytest tests/ -v - wszystkie testy przechodza
- [ ] pytest --cov=app - pokrycie >= 80%
- [ ] POST /api/translate z polskim tekstem zwraca JSON z translated_text i audio_id
- [ ] GET /api/audio/{audio_id} zwraca plik audio z Content-Type: audio/wav
- [ ] GET /api/health zwraca {"status": "ok", ...}
- [ ] UI w przegladarce: klikniecie "Tlumacz i odtworz" odtwarza audio
- [ ] Zadna zaleznosc w requirements.txt nie wymaga GPU
- [ ] .env.example zawiera wszystkie wymagane zmienne srodowiskowe

---

## 13. Decyzje (rozstrzygniete)

1. **Model glosowy Piper:** en_US-lessac-medium (ok. 60MB) - wybrany dla szybkosci na CPU.
2. **Format audio:** WAV (bez kompresji, brak zaleznosci od ffmpeg) w v1.
3. **Limit tekstu:** 5000 znakow.
