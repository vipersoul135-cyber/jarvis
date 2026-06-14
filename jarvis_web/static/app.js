document.addEventListener("DOMContentLoaded", () => {
    // Determine websocket URL
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    let ws = new WebSocket(wsUrl);
    
    const cpuBar = document.getElementById("cpu-bar");
    const cpuText = document.getElementById("cpu-text");
    const ramBar = document.getElementById("ram-bar");
    const ramText = document.getElementById("ram-text");
    const chatBox = document.getElementById("chat-box");
    const cmdInput = document.getElementById("cmd-input");
    const sendBtn = document.getElementById("send-btn");
    const voiceStatus = document.getElementById("voice-status");

    function connect() {
        ws.onopen = () => {
            console.log("WebSocket connected.");
            // Start polling for stats
            setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ action: "get_stats" }));
                }
            }, 2000);
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === "stats") {
                // Update CPU
                cpuBar.style.width = `${data.cpu}%`;
                cpuText.textContent = `${data.cpu.toFixed(1)}%`;
                
                // Update RAM
                ramBar.style.width = `${data.ram}%`;
                ramText.textContent = `${data.ram.toFixed(1)}%`;
                
            } else if (data.type === "chat") {
                const senderClass = data.sender.toLowerCase() === "user" ? "user" : "jarvis";
                addMessage(senderClass, data.text);
                
                if (senderClass === "jarvis") {
                    voiceStatus.textContent = "SPEAKING...";
                    document.querySelector(".arc-reactor").classList.add("speaking");
                    // _jarvisSpeakWithMic is set up below if mic is available
                    const speakFn = window._jarvisSpeakWithMic || jarvisSpeak;
                    speakFn(data.text, () => {
                        voiceStatus.textContent = "AWAITING COMMAND";
                        document.querySelector(".arc-reactor").classList.remove("speaking");
                    });
                }
            }
        };

        ws.onclose = () => {
            console.log("WebSocket disconnected. Retrying...");
            setTimeout(() => {
                ws = new WebSocket(wsUrl);
                connect();
            }, 3000);
        };
    }

    connect();

    function addMessage(senderClass, text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${senderClass}`;
        msgDiv.textContent = text;
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // ── Jarvis TTS via Web Speech API ─────────────────────────────────────────
    let currentUtterance = null;

    function pickDeepVoice(utter) {
        const voices = window.speechSynthesis.getVoices();
        const preferred = [
            'Microsoft Ryan Online (Natural) - English (United Kingdom)',
            'Google UK English Male',
            'Microsoft George - English (United Kingdom)',
        ];
        for (const name of preferred) {
            const match = voices.find(v => v.name.includes(name));
            if (match) { utter.voice = match; return; }
        }
        // fallback: pick any en-GB voice
        const gbVoice = voices.find(v => v.lang === 'en-GB');
        if (gbVoice) utter.voice = gbVoice;
    }

    function jarvisSpeak(text, onEnd) {
        if (!window.speechSynthesis) return;
        window.speechSynthesis.cancel();

        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = 'en-GB';
        utter.rate = 0.88;
        utter.pitch = 0.7;
        utter.volume = 1.0;

        if (window.speechSynthesis.getVoices().length) {
            pickDeepVoice(utter);
        } else {
            window.speechSynthesis.onvoiceschanged = () => pickDeepVoice(utter);
        }

        utter.onend = () => { if (onEnd) onEnd(); };
        utter.onerror = () => { if (onEnd) onEnd(); };
        currentUtterance = utter;
        window.speechSynthesis.speak(utter);
    }
    // ─────────────────────────────────────────────────────────────────────────

    function sendCommand() {
        const text = cmdInput.value.trim();
        if (text && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: "command", text: text }));
            cmdInput.value = "";
            voiceStatus.textContent = "TRANSMITTING...";
        }
    }

    sendBtn.addEventListener("click", sendCommand);
    cmdInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendCommand();
        }
    });

    // ── Request mic permission immediately on page load ──────────────────────
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                // Permission granted — stop the stream, Speech API will use it
                stream.getTracks().forEach(t => t.stop());
                startRecognition();
            })
            .catch(err => {
                console.warn("Mic permission denied:", err);
                addMessage("system", "⚠️ Microphone access denied. Voice commands disabled.");
            });
    } else {
        startRecognition(); // fallback for older browsers
    }

    function startRecognition() {
        // Web Speech API for Microphone input
        const micBtn = document.getElementById("mic-btn");
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            micBtn.style.display = "none";
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        let isActive = false;       // recognition.start() has been called
        let isSpeaking = false;     // Jarvis TTS is playing right now
        let awaitingCommand = false; // wake word heard, next speech = command

        const WAKE_WORDS = ["hey jarvis", "jarvis", "hey travis", "hey davis"];
        function hasWakeWord(text) {
            return WAKE_WORDS.some(w => text.toLowerCase().includes(w));
        }

        // ── Mic control ──────────────────────────────────────────────────────
        function startMic() {
            if (isActive || isSpeaking) return;
            isActive = true;
            try { recognition.start(); } catch(e) { isActive = false; }
        }
        function stopMic() {
            isActive = false;
            try { recognition.stop(); } catch(e) {}
        }

        // ── Speak the "I'm listening" ack ─────────────────────────────────────
        // Stops mic while speaking, then restarts in command mode after done
        function speakAck(text) {
            if (!window.speechSynthesis) {
                // No speech synthesis — just restart mic directly
                setTimeout(startMic, 300);
                return;
            }
            isSpeaking = true;  // ← blocks mic from restarting in onend
            stopMic();
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance(text);
            u.lang = 'en-GB'; u.rate = 0.88; u.pitch = 0.7; u.volume = 1.0;
            pickDeepVoice(u);
            u.onend = () => {
                isSpeaking = false;
                // Wait 500ms after Jarvis finishes talking before opening mic
                // so the mic doesn't catch audio reverb / tail
                setTimeout(startMic, 500);
            };
            u.onerror = () => {
                isSpeaking = false;
                setTimeout(startMic, 300);
            };
            window.speechSynthesis.speak(u);
        }

        // ── Speak a full Jarvis reply (pause mic while talking) ──────────────
        window._jarvisSpeakWithMic = function(text, onEnd) {
            isSpeaking = true;
            stopMic();
            jarvisSpeak(text, () => {
                isSpeaking = false;
                awaitingCommand = false;
                if (onEnd) onEnd();
                setTimeout(startMic, 500);
            });
        };

        // ── Recognition events ───────────────────────────────────────────────
        recognition.onstart = function() {
            isActive = true;
            micBtn.style.color = awaitingCommand ? "#00ff88" : "#ff007f";
            micBtn.style.textShadow = awaitingCommand
                ? "0 0 10px #00ff88" : "0 0 10px #ff007f";
            voiceStatus.textContent = awaitingCommand ? "SPEAK YOUR COMMAND..." : "AWAITING COMMAND";
        };

        recognition.onresult = function(event) {
            const lastResult = event.results[event.results.length - 1];
            if (!lastResult.isFinal) return;
            const transcript = lastResult[0].transcript.trim();

            if (!awaitingCommand) {
                // Phase 1: silent — only react to wake word
                if (hasWakeWord(transcript)) {
                    awaitingCommand = true;
                    voiceStatus.textContent = "LISTENING...";
                    micBtn.style.color = "#00ff88";
                    micBtn.style.textShadow = "0 0 10px #00ff88";
                    addMessage("jarvis", "I'm listening, sir.");
                    speakAck("I'm listening, sir.");
                    // mic restarts ONLY after speakAck finishes (via u.onend)
                }
                // else: completely ignored
            } else {
                // Phase 2: command received
                awaitingCommand = false;
                voiceStatus.textContent = "PROCESSING...";
                cmdInput.value = transcript;
                sendCommand();
            }
        };

        recognition.onerror = function(event) {
            isActive = false;
            if (event.error === "not-allowed" || event.error === "service-not-allowed") {
                addMessage("system", "⚠️ Mic blocked by browser. Please allow microphone access.");
                return;
            }
            // no-speech or aborted — restart if not blocked by speech
            if (!isSpeaking) setTimeout(startMic, 300);
        };

        recognition.onend = function() {
            isActive = false;
            micBtn.style.color = awaitingCommand ? "#00ff88" : "#ff007f";
            micBtn.style.textShadow = awaitingCommand
                ? "0 0 10px #00ff88" : "0 0 10px #ff007f";
            // Only auto-restart if Jarvis is NOT speaking
            // (if isSpeaking, speakAck/jarvisSpeak will call startMic when done)
            if (!isSpeaking) {
                setTimeout(startMic, 250);
            }
        };


        // Patch the WS handler to use _jarvisSpeakWithMic
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === "stats") {
                cpuBar.style.width = `${data.cpu}%`;
                cpuText.textContent = `${data.cpu.toFixed(1)}%`;
                ramBar.style.width = `${data.ram}%`;
                ramText.textContent = `${data.ram.toFixed(1)}%`;
            } else if (data.type === "chat") {
                const senderClass = data.sender.toLowerCase() === "user" ? "user" : "jarvis";
                addMessage(senderClass, data.text);
                if (senderClass === "jarvis") {
                    voiceStatus.textContent = "SPEAKING...";
                    document.querySelector(".arc-reactor").classList.add("speaking");
                    window._jarvisSpeakWithMic(data.text, () => {
                        voiceStatus.textContent = "AWAITING COMMAND";
                        document.querySelector(".arc-reactor").classList.remove("speaking");
                    });
                }
            }
        };

        // Kick off!
        startMic();
    }
});
