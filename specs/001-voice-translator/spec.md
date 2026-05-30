# Specyfikacja: Aplikacja do nauki jezykow przez tlumaczenie z odsluchem

- **Wersja:** 1.2
- **Data:** 2026-05-30
- **Branch:** 001-voice-translator
- **Jezyk interfejsu:** Polski
- **Jezyk kodu:** Angielski (nazwy zmiennych, funkcji, komentarze)

> Zmiany w 1.2 wzgledem 1.0: dodano historie ostatnich 5 tlumaczen (trwala, localStorage),
> przyciski Play przy kazdym wpisie, uklad wpisu (PL mala czcionka / EN duza czcionka).
> Czas zycia audio wydluzony z 1h do 24h, aby Play dzialal dla calej historii.
> WAZNE: tryb tekstowy jest CICHY - brak auto-odtwarzania; dzwiek gra TYLKO po klikniecu Play
> (uzytek w miejscach publicznych, np. sklep). Tryb mikrofonu pozostaje poza zakresem v1.

---

## 1. Cel projektu

Minimalna, dzialajaca aplikacja webowa, ktora pozwala uzytkownikowi:

- Wpisac lub wkleic tekst po polsku
- Kliknac jeden przycisk, by otrzymac tlumaczenie na angielski wyswietlone jako tekst (bez dzwieku)
- Odtworzyc wymowe tlumaczenia na zadanie, klikajac przycisk Play
- Widziec historie ostatnich 5 tlumaczen i odtwarzac kazde przyciskiem Play

**Uzytkownik:** osoba uczaca sie angielskiego, korzysta z przegladarki na telefonie lub komputerze.

**Kryterium sukcesu v1:** Uzytkownik wpisuje zdanie po polsku, klika "Tlumacz", widzi angielskie tlumaczenie jako tekst (BEZ automatycznego dzwieku), tlumaczenie zostaje zapisane na szczycie historii ostatnich 5, a dzwiek odtwarza sie dopiero po klikniecu Play. Dziala dyskretnie w miejscach publicznych.

---

## 2. Stos technologiczny

| Warstwa | Technologia |
|---|---|
| Backend | Python 3.11+ + FastAPI |
| Tlumaczenie | DeepL API (REST), biblioteka deepl-python |
| Synteza mowy | Piper TTS (CPU-only, offline, licencja MIT) |
| Serwowanie statyki | FastAPI StaticFiles |
| Frontend | HTML5 + CSS3 + Vanilla JS (bez frameworka) |
| Historia (trwala) | localStorage przegladarki (po stronie frontendu, bez bazy danych) |
| Testy | pytest + pytest-asyncio + httpx AsyncClient |
| Zaleznosci | pip + requirements.txt |
| Konfiguracja | python-dotenv + .env |

**Ograniczenie krytyczne:** Zero zaleznosci od GPU. Piper dziala wylacznie na CPU.

---

## 3. Komendy

```
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest tests/ -v
pytest tests/ -v --cov=app --cov-report=term-missing
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
│   └── app.js               # Logika: fetch API, historia 5 w localStorage, Play
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

Bledy: 400 (pusty tekst), 422 (walidacja Pydantic), 503 (DeepL niedostepny), 500 (wewnetrzny).

Logika:
1. Walidacja wejscia (nie pusty, max 5000 znakow)
2. Tlumaczenie przez DeepL (PL -> EN-US)
3. Synteza mowy przez Piper -> plik WAV
4. Zapis pliku audio do katalogu tymczasowego z unikalnym audio_id
5. Zwrot JSON z audio_id

### GET /api/audio/{audio_id}

Odpowiedz (200 OK): plik audio (audio/wav). Bledy: 404 (nie istnieje lub wygasl).

Logika: Serwuje plik z katalogu tymczasowego. Pliki starsze niz AUDIO_MAX_AGE_SECONDS moga byc usuwane (czyszczenie przy starcie). UWAGA: czas zycia ustawiony na 24h, aby przyciski Play w historii ostatnich 5 tlumaczen dzialaly przez cala sesje nauki w obrebie dnia.

### GET /api/health

Odpowiedz: `{"status": "ok", "deepl": "available", "tts": "available"}`. Status, nie HTTP 503.

---

## 6. Interfejs uzytkownika (Polski)

Jeden ekran, responsywny (dziala na telefonie).

### 6.1 Glowny obszar tlumaczenia
- Pole tekstowe (textarea) na tekst po polsku
- Przycisk "Tlumacz"
- Po tlumaczeniu: angielski tekst pojawia sie od razu, ale **BEZ dzwieku** (tryb cichy)
- Obok tlumaczenia przycisk **Play** - dzwiek gra TYLKO po jego klikniecu
- Uzasadnienie: narzedzie ma dzialac dyskretnie w miejscach publicznych (np. sklep), gdzie
  uzytkownik czyta tlumaczenie wzrokiem i nie chce, by telefon odtwarzal dzwiek automatycznie

### 6.2 Historia ostatnich 5 tlumaczen
- Pod glownym obszarem wyswietlana jest lista **maksymalnie 5 ostatnich tlumaczen**
- **Kolejka (FIFO):** najnowsze tlumaczenie pojawia sie na **szczycie** listy; gdy wpisow jest wiecej niz 5, **najstarszy (na dole) znika**
- Historia jest **trwala** - zapisywana w localStorage przegladarki, przezywa odswiezenie strony i ponowne otwarcie aplikacji na tym samym urzadzeniu
- Kazdy wpis localStorage przechowuje: original_text (PL), translated_text (EN), audio_id, target_lang

### 6.3 Uklad pojedynczego wpisu historii
Kazdy wpis na liscie pokazuje:
- **Polski oryginal** - mniejsza czcionka (np. szary, drugorzedny), zeby wiedziec o co chodzi (np. "Dzien dobry")
- **Angielskie tlumaczenie** - wieksza czcionka, glowny element wpisu (np. "Good morning")
- **Przycisk Play** - odtwarza audio danego wpisu, wolajac GET /api/audio/{audio_id}

### 6.4 Stany UI
- **Poczatkowy:** textarea + przycisk aktywny; historia z localStorage (jesli istnieje)
- **Ladowanie:** przycisk nieaktywny, tekst "Tlumacze...", spinner
- **Sukces:** nowe tlumaczenie wyswietlone jako tekst (CISZA, bez dzwieku) + dodane na szczyt historii; przycisk Play dostepny
- **Blad:** komunikat po polsku

### 6.5 Teksty interfejsu (po polsku)

| Element | Tekst |
|---|---|
| Tytul strony | Tlumacz i ucz sie |
| Naglowek | Tlumacz i ucz sie angielskiego |
| Placeholder textarea | Wpisz lub wklej tekst po polsku... |
| Przycisk glowny | Tlumacz |
| Przycisk glowny (ladowanie) | Tlumacze... |
| Naglowek sekcji historii | Ostatnie tlumaczenia |
| Przycisk Play (przy tlumaczeniu i przy wpisach) | Play (ikona ▶) |
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
AUDIO_MAX_AGE_SECONDS=86400
MAX_TEXT_LENGTH=5000
```

> AUDIO_MAX_AGE_SECONDS = 86400 (24h). Wydluzone z 3600 (1h), aby przyciski Play
> w historii ostatnich 5 tlumaczen dzialaly przez caly dzien nauki.

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
| Brak w v1 | E2E, testy frontendu (w tym logika localStorage) | - |

Zasady:
- Zewnetrzne API (DeepL) ZAWSZE mockowane - nie wolno odpytywac prawdziwego API
- Piper TTS mockowany - testy generuja falszywy plik WAV
- Kazdy endpoint ma test dla sciezki szczesliwej i glownych bledow (400, 503)
- Pokrycie: minimum 80% dla kodu w app/

---

## 10. Projekt pod przyszle rozszerzenia (NIE budowac w v1)

| Przyszla funkcja | Jak v1 to umozliwia |
|---|---|
| **Tryb mikrofonu (STT)** | Nacisnij start -> mow -> nacisnij stop -> rozpoznanie mowy (Whisper) -> istniejacy pipeline tlumaczenia. Nowy router POST /api/transcribe. Wymaga modelu Whisper (CPU). POZA ZAKRESEM v1. |
| Wiele jezykow docelowych | Pole target_lang juz jest w API; UI dostanie <select> |
| PWA (instalowalna na telefonie) | Statyczny frontend -> dodac manifest.json + service-worker.js |
| VPS bez GPU | Piper CPU-only juz teraz; wdrozenie calosci na tani VPS bez GPU |
| Historia ponad-urzadzeniowa | Obecnie localStorage (per urzadzenie); mozna przeniesc na backend (plik/baza) |

---

## 11. Granice (Boundaries)

**Zawsze:**
- Uruchom pytest przed zgloszeniem zmiany
- Waliduj dane wejsciowe na poziomie Pydantic
- Loguj bledy zewnetrznych API z pelnym traceback (exc_info=True)
- Trzymaj klucz API wylacznie w .env, nigdy w kodzie

**Zapytaj najpierw:**
- Zmiana silnika TTS, dodanie bazy danych, zmiana domyslnego jezyka, dodanie uwierzytelniania

**Nigdy:**
- Nie commituj .env z prawdziwym kluczem
- Nie dodawaj zaleznosci wymagajacych GPU
- Nie usuwaj testow zamiast naprawiac kod
- Nie odpytuj DeepL API w testach automatycznych

---

## 12. Kryteria sukcesu (testowalne)

- [ ] pytest tests/ -v - wszystkie testy przechodza
- [ ] pytest --cov=app - pokrycie >= 80%
- [ ] POST /api/translate zwraca JSON z translated_text i audio_id
- [ ] GET /api/audio/{audio_id} zwraca plik audio/wav
- [ ] GET /api/health zwraca {"status": "ok", ...}
- [ ] UI: klikniecie "Tlumacz" wyswietla tekst BEZ automatycznego dzwieku (tryb cichy)
- [ ] UI: dzwiek odtwarza sie wylacznie po klikniecu Play
- [ ] UI: nowe tlumaczenie pojawia sie na szczycie historii; lista trzyma max 5
- [ ] UI: kazdy wpis ma PL (mala czcionka) + EN (duza czcionka) + dzialajacy Play
- [ ] UI: historia przezywa odswiezenie strony (localStorage)
- [ ] Zadna zaleznosc w requirements.txt nie wymaga GPU
- [ ] AUDIO_MAX_AGE_SECONDS = 86400

---

## 13. Decyzje (rozstrzygniete)

1. **Model glosowy Piper:** en_US-lessac-medium (ok. 60MB).
2. **Format audio:** WAV (bez kompresji, brak zaleznosci od ffmpeg).
3. **Limit tekstu:** 5000 znakow.
4. **Historia:** 5 ostatnich, trwala w localStorage przegladarki (per urzadzenie).
5. **Audio:** tryb tekstowy CICHY - bez auto-odtwarzania; dzwiek tylko po klikniecu Play (przy nowym tlumaczeniu i przy wpisach historii); czas zycia audio 24h.
6. **Mikrofon:** poza zakresem v1, dodany jako osobny modul pozniej.
