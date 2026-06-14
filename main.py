import sys
import os
import logging
from PyQt6.QtWidgets import QApplication

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Ensure the current directory is in the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from jarvis_core.database import JarvisDatabase
from jarvis_system.monitor import SystemMonitor
from jarvis_core.voice_engine import VoiceEngine
from jarvis_ui.main_window import JarvisMainWindow

# Setup root logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    # 1. Initialize Core Components
    db = JarvisDatabase()
    sys_monitor = SystemMonitor()
    def voice_callback(event_type, data):
        import re
        import subprocess
        import webbrowser
        import os
        import asyncio
        from jarvis_web.server import manager, process_web_command

        # Helper to broadcast to the web UI asynchronously
        def send_to_ui(message_dict):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(manager.broadcast(json.dumps(message_dict)))
            loop.close()

        if event_type == "wake":
            logging.info("Broadcasting wake event to UI")
            send_to_ui({"type": "chat", "sender": "System", "text": "🎙️ Wake word detected! Listening for command..."})
        
        elif event_type == "speak":
            send_to_ui({"type": "chat", "sender": "Jarvis", "text": data})
            
        elif event_type == "command":
            import json
            logging.info(f"[Voice Command Received] {data}")
            send_to_ui({"type": "chat", "sender": "User", "text": f"🗣️ {data}"})
            
            lower_text = data.lower().strip()
            
            APP_MAPPING = {
                # ── Browsers ────────────────────────────────────────────────
                "chrome": "chrome",
                "google chrome": "chrome",
                "edge": "msedge",
                "microsoft edge": "msedge",
                "firefox": "firefox",
                "mozilla firefox": "firefox",
                "opera": "opera",
                "brave": "brave",
                "brave browser": "brave",

                # ── Web / Streaming ─────────────────────────────────────────
                "youtube": "https://www.youtube.com",
                "you tube": "https://www.youtube.com",
                "google": "https://google.com",
                "gmail": "https://mail.google.com",
                "google mail": "https://mail.google.com",
                "github": "https://github.com",
                "netflix": "https://www.netflix.com",
                "hotstar": "https://www.hotstar.com",
                "disney hotstar": "https://www.hotstar.com",
                "prime video": "https://www.primevideo.com",
                "amazon prime": "https://www.primevideo.com",
                "twitch": "https://www.twitch.tv",
                "instagram": "https://www.instagram.com",
                "twitter": "https://www.twitter.com",
                "x": "https://www.x.com",
                "facebook": "https://www.facebook.com",
                "whatsapp": "https://web.whatsapp.com",
                "reddit": "https://www.reddit.com",
                "linkedin": "https://www.linkedin.com",
                "stack overflow": "https://stackoverflow.com",
                "chat gpt": "https://chat.openai.com",
                "chatgpt": "https://chat.openai.com",
                "openai": "https://chat.openai.com",
                "gemini": "https://gemini.google.com",
                "google gemini": "https://gemini.google.com",

                # ── Music & Media ───────────────────────────────────────────
                "spotify": "spotify",
                "vlc": "vlc",
                "vlc media player": "vlc",
                "media player": "wmplayer",
                "windows media player": "wmplayer",
                "groove music": "mswindowsmusic",
                "itunes": "itunes",

                # ── Communication ───────────────────────────────────────────
                "discord": "discord",
                "telegram": "telegram",
                "zoom": "zoom",
                "teams": "teams",
                "microsoft teams": "teams",
                "skype": "skype",
                "slack": "slack",

                # ── Microsoft Office ───────────────────────────────────────
                "word": "winword",
                "microsoft word": "winword",
                "excel": "excel",
                "microsoft excel": "excel",
                "powerpoint": "powerpnt",
                "microsoft powerpoint": "powerpnt",
                "outlook": "outlook",
                "microsoft outlook": "outlook",
                "onenote": "onenote",
                "access": "msaccess",

                # ── Dev Tools ──────────────────────────────────────────────
                "vs code": "code",
                "vscode": "code",
                "visual studio code": "code",
                "visual studio": "devenv",
                "notepad plus plus": "notepad++",
                "notepad++": "notepad++",
                "sublime": "sublime_text",
                "sublime text": "sublime_text",
                "android studio": "studio64",
                "pycharm": "pycharm64",
                "intellij": "idea64",
                "git bash": "git-bash",
                "postman": "postman",
                "docker": "docker desktop",

                # ── System Tools ───────────────────────────────────────────
                "notepad": "notepad",
                "calculator": "calc",
                "file explorer": "explorer",
                "explorer": "explorer",
                "task manager": "taskmgr",
                "command prompt": "cmd",
                "cmd": "cmd",
                "powershell": "powershell",
                "registry editor": "regedit",
                "paint": "mspaint",
                "snipping tool": "snippingtool",
                "control panel": "control",
                "settings": "ms-settings:",
                "windows settings": "ms-settings:",
                "device manager": "devmgmt.msc",
                "disk management": "diskmgmt.msc",
                "event viewer": "eventvwr.msc",

                # ── Games & Launchers ──────────────────────────────────────
                "steam": "steam",
                "epic games": "epicgameslauncher",
                "epic": "epicgameslauncher",
                "xbox": "xboxapp",
                "minecraft": "minecraft",
                "roblox": "roblox",

                # ── Creative & Design ───────────────────────────────────────
                "photoshop": "photoshop",
                "adobe photoshop": "photoshop",
                "premiere": "premiere pro",
                "adobe premiere": "premiere pro",
                "after effects": "afterfx",
                "figma": "figma",
                "canva": "https://www.canva.com",
            }
            
            # Execute command synchronously
            if lower_text.startswith("open ") or lower_text.startswith("start "):
                spoken_app = lower_text.split(" ", 1)[1].strip(".,!?")
                app_cmd = APP_MAPPING.get(spoken_app, spoken_app)
                if "http" in app_cmd:
                    webbrowser.open(app_cmd)
                else:
                    try:
                        from AppOpener import open as appopen
                        appopen(spoken_app, match_closest=True)
                    except:
                        subprocess.Popen(f"start {app_cmd}", shell=True)
                voice_engine.speak(f"Opening {spoken_app}")
            elif lower_text.startswith("close ") or lower_text.startswith("kill "):
                spoken_app = lower_text.split(" ", 1)[1].strip(".,!?")
                app_cmd = APP_MAPPING.get(spoken_app, spoken_app)

                # Map web/URL apps to their real process so we only kill that one
                WEB_PROCESS_MAP = {
                    "youtube": "chrome.exe",
                    "you tube": "chrome.exe",
                    "google": "chrome.exe",
                    "gmail": "chrome.exe",
                    "google mail": "chrome.exe",
                    "github": "chrome.exe",
                    "netflix": "chrome.exe",
                    "hotstar": "chrome.exe",
                    "disney hotstar": "chrome.exe",
                    "prime video": "chrome.exe",
                    "amazon prime": "chrome.exe",
                    "twitch": "chrome.exe",
                    "instagram": "chrome.exe",
                    "twitter": "chrome.exe",
                    "x": "chrome.exe",
                    "facebook": "chrome.exe",
                    "whatsapp": "chrome.exe",
                    "reddit": "chrome.exe",
                    "linkedin": "chrome.exe",
                    "chatgpt": "chrome.exe",
                    "chat gpt": "chrome.exe",
                    "openai": "chrome.exe",
                    "gemini": "chrome.exe",
                    "canva": "chrome.exe",
                    "stack overflow": "chrome.exe",
                }

                try:
                    from AppOpener import close as appclose
                    appclose(spoken_app, match_closest=True)
                except:
                    if "http" in app_cmd:
                        proc = WEB_PROCESS_MAP.get(spoken_app.lower(), "chrome.exe")
                        os.system(f"taskkill /f /im {proc}")
                    else:
                        os.system(f"taskkill /f /im {app_cmd}.exe")
                voice_engine.speak(f"Closing {spoken_app}")
            elif "search for " in lower_text:
                query = lower_text.split("search for ")[1].strip(".,!?")
                webbrowser.open(f"https://www.google.com/search?q={query}")
                voice_engine.speak(f"Searching for {query}")
            else:
                voice_engine.speak("I heard you, but I do not have a specific action for that yet.")

    voice_engine = VoiceEngine(db=db, callback=voice_callback)
    
    core_system = {
        'db': db,
        'system': sys_monitor,
        'voice': voice_engine
    }

    # Start listening immediately in the background since UI is disabled
    voice_engine.start_background_listening()

    # 1.5 Launch Background Web Dashboard
    from jarvis_web.server import start_server_in_background
    start_server_in_background(core_system)

    import time
    import webbrowser
    
    logging.info("===================================================")
    logging.info(" JARVIS Web Dashboard is running locally!")
    logging.info(" Opening http://localhost:8000 in your browser...")
    logging.info("===================================================")
    
    # Auto-open browser
    webbrowser.open("http://localhost:8000")
    
    # Keep the main thread alive so the background server continues running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("JARVIS shutting down...")

if __name__ == "__main__":
    main()
