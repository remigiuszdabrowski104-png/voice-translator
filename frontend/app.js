(function () {
    "use strict";

    // --- Constants ---
    var MAX_HISTORY = 5;
    var STORAGE_KEY = "voice-translator-history";

    // --- DOM references ---
    var sourceTextEl = document.getElementById("source-text");
    var translateBtn = document.getElementById("translate-btn");
    var errorMsgEl = document.getElementById("error-message");
    var resultAreaEl = document.getElementById("result-area");
    var resultPlEl = document.getElementById("result-pl");
    var resultEnEl = document.getElementById("result-en");
    var resultPlayBtn = document.getElementById("result-play-btn");
    var historyListEl = document.getElementById("history-list");

    // --- State ---
    var currentAudioId = null;
    var history = [];

    // --- localStorage helpers ---

    function loadHistory() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {
                var parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) {
                    return parsed.slice(0, MAX_HISTORY);
                }
            }
        } catch (e) {
            // Corrupt data – reset.
        }
        return [];
    }

    function saveHistory() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
        } catch (e) {
            // Storage full or unavailable – silently ignore.
        }
    }

    // --- Audio playback ---

    function playAudio(audioId) {
        if (!audioId) return;
        var url = "/api/audio/" + encodeURIComponent(audioId);
        var audio = new Audio(url);
        audio.play().catch(function () {
            // Autoplay policy may block; that's acceptable.
        });
    }

    // --- History rendering ---

    function renderHistory() {
        historyListEl.innerHTML = "";

        for (var i = 0; i < history.length; i++) {
            var entry = history[i];

            var li = document.createElement("li");
            li.className = "history-entry";

            var plSpan = document.createElement("span");
            plSpan.className = "history-pl";
            plSpan.textContent = entry.original_text;

            var enSpan = document.createElement("span");
            enSpan.className = "history-en";
            enSpan.textContent = entry.translated_text;

            var playBtn = document.createElement("button");
            playBtn.className = "btn btn-play";
            playBtn.title = "Odtwórz wymowę";
            playBtn.innerHTML = '<span class="play-icon">&#9654;</span> Play';

            (function (audioId) {
                playBtn.addEventListener("click", function () {
                    playAudio(audioId);
                });
            })(entry.audio_id);

            li.appendChild(plSpan);
            li.appendChild(enSpan);
            li.appendChild(playBtn);
            historyListEl.appendChild(li);
        }
    }

    // --- Add entry to history (FIFO, max 5) ---

    function addToHistory(originalText, translatedText, audioId, targetLang) {
        // Prepend newest entry.
        history.unshift({
            original_text: originalText,
            translated_text: translatedText,
            audio_id: audioId,
            target_lang: targetLang
        });

        // Drop oldest entries if exceeding MAX_HISTORY.
        if (history.length > MAX_HISTORY) {
            history = history.slice(0, MAX_HISTORY);
        }

        saveHistory();
        renderHistory();
    }

    // --- Result display (silent – no auto-play) ---

    function showResult(originalText, translatedText, audioId) {
        currentAudioId = audioId;
        resultPlEl.textContent = originalText;
        resultEnEl.textContent = translatedText;
        resultAreaEl.hidden = false;
        resultPlayBtn.hidden = false;

        // IMPORTANT: Do NOT auto-play. Audio plays only on user click.
        resultPlayBtn.onclick = function () {
            playAudio(audioId);
        };
    }

    function hideResult() {
        resultAreaEl.hidden = true;
        currentAudioId = null;
    }

    // --- UI state helpers ---

    function showError(message) {
        errorMsgEl.textContent = message;
        errorMsgEl.hidden = false;
    }

    function hideError() {
        errorMsgEl.hidden = true;
    }

    function setLoading(isLoading) {
        if (isLoading) {
            translateBtn.disabled = true;
            translateBtn.innerHTML = '<span class="spinner"></span>Tłumaczę...';
        } else {
            translateBtn.disabled = false;
            translateBtn.textContent = "Tłumacz";
        }
    }

    function getErrorMessage(status) {
        switch (status) {
            case 400:
                return "Wpisz tekst przed tłumaczeniem.";
            case 422:
                return "Tekst jest zbyt długi (max 5000 znaków).";
            default:
                return "Wystąpił błąd. Spróbuj ponownie.";
        }
    }

    // --- Translate action ---

    function doTranslate() {
        var text = sourceTextEl.value.trim();

        if (!text) {
            showError("Wpisz tekst przed tłumaczeniem.");
            return;
        }

        hideError();
        hideResult();
        setLoading(true);

        fetch("/api/translate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: text,
                target_lang: "EN-US"
            })
        })
            .then(function (response) {
                if (!response.ok) {
                    // Read body to prevent connection reuse issues.
                    return response.text().then(function () {
                        throw new Error(String(response.status));
                    });
                }
                return response.json();
            })
            .then(function (data) {
                showResult(data.original_text, data.translated_text, data.audio_id);
                addToHistory(
                    data.original_text,
                    data.translated_text,
                    data.audio_id,
                    data.target_lang
                );
                sourceTextEl.value = "";
            })
            .catch(function (err) {
                // err.message is the HTTP status code string or a network error.
                var statusCode = parseInt(err.message, 10);
                if (isNaN(statusCode)) {
                    // Network error or other.
                    showError("Wystąpił błąd. Spróbuj ponownie.");
                } else {
                    showError(getErrorMessage(statusCode));
                }
            })
            .finally(function () {
                setLoading(false);
            });
    }

    // --- Initialisation ---

    function init() {
        history = loadHistory();
        renderHistory();
        hideResult();
        hideError();

        translateBtn.addEventListener("click", doTranslate);

        // Allow Enter key (without Shift) to trigger translation.
        sourceTextEl.addEventListener("keydown", function (e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                doTranslate();
            }
        });
    }

    // Kick off when DOM is ready.
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();