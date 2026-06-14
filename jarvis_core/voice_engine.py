import logging
import threading
import queue
import time
import asyncio
import pvporcupine
import struct
import pyaudio
from faster_whisper import WhisperModel
import edge_tts
import os
import platform

logger = logging.getLogger(__name__)

class VoiceEngine:
    def __init__(self, db, callback=None):
        self.db = db
        self.callback = callback
        self.is_listening = False
        self.audio_queue = queue.Queue()
        
        self.wake_word = self.db.get_setting("wake_word", "jarvis")
        self.picovoice_key = self.db.get_setting("picovoice_key", "")
        
        self.porcupine = None
        self.pa = None
        self.audio_stream = None
        
        # Load Faster-Whisper Model (offline STT)
        # Disabled temporarily to prevent CTranslate2 hard crashes on unsupported CPUs
        self.whisper = None

    def start_background_listening(self):
        try:
            import vosk
            import json
            logger.info("Loading offline Vosk model for wake word detection...")
            self.model = vosk.Model(lang="en-us")
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
            
            self.pa = pyaudio.PyAudio()
            self.audio_stream = self.pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=8000
            )
            
            self.is_listening = True
            threading.Thread(target=self._listen_loop, daemon=True).start()
            logger.info("Background wake word listening started (Offline Mode).")
            return True
        except Exception as e:
            logger.error(f"Failed to start offline voice engine: {e}")
            return False

    def _listen_loop(self):
        import json
        while self.is_listening and self.audio_stream:
            try:
                data = self.audio_stream.read(4000, exception_on_overflow=False)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        logger.info(f"[Mic Heard Final]: {text}")
                        if self.callback:
                            self.callback("command", text)
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                time.sleep(1)

    def speak(self, text):
        """Natural TTS using edge-tts."""
        if not text:
            return
            
        if self.callback:
            self.callback("speak", text)
            
        try:
            # Run async edge-tts in a new event loop
            def run_tts():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # en-GB-RyanNeural — deep cinematic British male voice (classic Jarvis)
                communicate = edge_tts.Communicate(text, "en-GB-RyanNeural")
                mp3_path = os.path.abspath("temp_tts.mp3")
                loop.run_until_complete(communicate.save(mp3_path))
                
                # Play the audio using Windows MediaPlayer and wait for actual duration
                if platform.system() == "Windows":
                    import subprocess
                    # Estimate duration: ~150 words/min, 0.4s per word minimum
                    word_count = len(text.split())
                    estimated_secs = max(2, int(word_count * 0.45) + 1)
                    ps_script = (
                        f"Add-Type -AssemblyName presentationCore; "
                        f"$player = New-Object system.windows.media.mediaplayer; "
                        f"$player.open('{mp3_path}'); "
                        f"$player.Play(); "
                        f"Start-Sleep -Seconds {estimated_secs}"
                    )
                    subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
                
            threading.Thread(target=run_tts, daemon=True).start()
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            
    def stop(self):
        self.is_listening = False
        if self.audio_stream:
            self.audio_stream.close()
        if self.pa:
            self.pa.terminate()
