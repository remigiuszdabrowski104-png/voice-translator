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
    var micBtn = document.getElementById("mic-btn");
    var micStatusEl = document.getElementById("mic-status");

    // --- State ---
    var currentAudioId = null;
    var currentAudio = null;
    var history = [];
    var mediaRecorder = null;
    var audioChunks = [];
    var isRecording = false;

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
        // Zatrzymaj i zresetuj poprzednie odtwarzanie, zanim zagrasz od nowa.
        if (currentAudio) {
            currentAudio.pause();
            currentAudio.currentTime = 0;
        }
        currentAudio = new Audio(url);
        currentAudio.play().catch(function () {
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

    // --- Microphone / voice transcription ---

    function pickMimeType() {
        if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) {
            return "audio/mp4";
        }
        var types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/aac"];
        for (var i = 0; i < types.length; i++) {
            if (MediaRecorder.isTypeSupported(types[i])) {
                return types[i];
            }
        }
        return "";
    }

    function getExtension(mimeType) {
        if (mimeType.indexOf("mp4") !== -1 || mimeType.indexOf("aac") !== -1 || mimeType.indexOf("m4a") !== -1) {
            return "recording.m4a";
        }
        return "recording.webm";
    }

    function updateMicBtn(labelHtml, recordingClass) {
        micBtn.innerHTML = labelHtml;
        if (recordingClass) {
            micBtn.classList.add("recording");
        } else {
            micBtn.classList.remove("recording");
        }
    }

    function getTranscribeError(status) {
        switch (status) {
            case 413:
                return "Nagranie jest za długie.";
            case 503:
                return "Rozpoznawanie mowy nie jest skonfigurowane.";
            case 502:
                return "Usługa rozpoznawania mowy jest niedostępna.";
            case 400:
                return "Nagranie jest puste.";
            default:
                return "Nie udało się rozpoznać mowy. Spróbuj ponownie.";
        }
    }

    function startRecording() {
        isRecording = true;
        hideError();
        updateMicBtn("&#127908; Stop", true);
        micStatusEl.textContent = "Nagrywam...";
        micStatusEl.hidden = false;

        navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
            var mimeType = pickMimeType();
            var options = mimeType ? { mimeType: mimeType } : {};
            mediaRecorder = new MediaRecorder(stream, options);
            audioChunks = [];

            mediaRecorder.ondataavailable = function (e) {
                if (e.data && e.data.size > 0) {
                    audioChunks.push(e.data);
                }
            };

            mediaRecorder.onstop = function () {
                var actualType = mimeType || "audio/webm";
                var blob = new Blob(audioChunks, { type: actualType });
                var tracks = stream.getTracks();
                for (var t = 0; t < tracks.length; t++) {
                    tracks[t].stop();
                }
                uploadAudio(blob, mimeType);
            };

            mediaRecorder.start();
        }).catch(function (err) {
            showError("Brak dostępu do mikrofonu.");
            isRecording = false;
            updateMicBtn("&#127908; Mów", false);
            micStatusEl.hidden = true;
        });
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            micBtn.disabled = true;
            isRecording = false;
            micStatusEl.textContent = "Rozpoznaję...";
            updateMicBtn("&#127908; Mów", false);
        }
    }

    function uploadAudio(blob, mimeType) {
        var form = new FormData();
        var ext = getExtension(blob.type || mimeType);
        form.append("audio", blob, ext);

        fetch("/api/transcribe", {
            method: "POST",
            body: form
        })
            .then(function (response) {
                if (!response.ok) {
                    return response.text().then(function () {
                        throw new Error(String(response.status));
                    });
                }
                return response.json();
            })
            .then(function (data) {
                sourceTextEl.value = data.text;
                doTranslate();
            })
            .catch(function (err) {
                var statusCode = parseInt(err.message, 10);
                if (isNaN(statusCode)) {
                    showError("Nie udało się rozpoznać mowy. Spróbuj ponownie.");
                } else {
                    showError(getTranscribeError(statusCode));
                }
            })
            .finally(function () {
                micBtn.disabled = false;
                micStatusEl.hidden = true;
                updateMicBtn("&#127908; Mów", false);
                isRecording = false;
            });
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

        // Microphone button – only if supported.
        if (navigator.mediaDevices && window.MediaRecorder) {
            micBtn.addEventListener("click", function () {
                if (isRecording) {
                    stopRecording();
                } else {
                    startRecording();
                }
            });
        } else {
            micBtn.hidden = true;
        }

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
