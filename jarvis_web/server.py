import os
import asyncio
import threading
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import re

logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static directory for CSS and JS
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# We will store the global core_system reference here
core_system = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.get("/")
async def get_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")
            
            if action == "get_stats":
                if core_system and 'system' in core_system:
                    cpu = core_system['system'].get_cpu_usage()
                    ram = core_system['system'].get_ram_usage()
                    await websocket.send_text(json.dumps({
                        "type": "stats",
                        "cpu": cpu,
                        "ram": ram
                    }))
                    
            elif action == "command":
                command = payload.get("text", "")
                await manager.broadcast(json.dumps({"type": "chat", "sender": "User", "text": command}))
                
                # Process command via background task to avoid blocking WS
                asyncio.create_task(process_web_command(command))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

import subprocess
import webbrowser

async def process_web_command(text):
    if not core_system:
        return
        
    lower_text = text.lower().strip()
    reply = None
    
    # Simple regex parsing matching the desktop app
    open_match = re.match(r"\b(?:open|launch|start)\s+(.+)", lower_text)
    close_match = re.match(r"\b(?:close|exit|terminate|kill|stop)\s+(.+)", lower_text)
    search_match = re.match(r"\b(?:search the web for|search google for|search for|google)\s+(.+)", lower_text)
    
    APP_MAPPING = {
        # ── Browsers ───────────────────────────────────────────────────
        "chrome": "chrome",
        "google chrome": "chrome",
        "edge": "msedge",
        "microsoft edge": "msedge",
        "firefox": "firefox",
        "mozilla firefox": "firefox",
        "opera": "opera",
        "brave": "brave",
        "brave browser": "brave",

        # ── Web / Streaming ────────────────────────────────────────────
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

        # ── Music & Media ──────────────────────────────────────────────
        "spotify": "spotify",
        "vlc": "vlc",
        "vlc media player": "vlc",
        "media player": "wmplayer",
        "windows media player": "wmplayer",
        "groove music": "mswindowsmusic",
        "itunes": "itunes",

        # ── Communication ──────────────────────────────────────────────
        "discord": "discord",
        "telegram": "telegram",
        "zoom": "zoom",
        "teams": "teams",
        "microsoft teams": "teams",
        "skype": "skype",
        "slack": "slack",

        # ── Microsoft Office ───────────────────────────────────────────
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

        # ── Dev Tools ──────────────────────────────────────────────────
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

        # ── System Tools ───────────────────────────────────────────────
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

        # ── Games & Launchers ──────────────────────────────────────────
        "steam": "steam",
        "epic games": "epicgameslauncher",
        "epic": "epicgameslauncher",
        "xbox": "xboxapp",
        "minecraft": "minecraft",
        "roblox": "roblox",

        # ── Creative & Design ──────────────────────────────────────────
        "photoshop": "photoshop",
        "adobe photoshop": "photoshop",
        "premiere": "premiere pro",
        "adobe premiere": "premiere pro",
        "after effects": "afterfx",
        "figma": "figma",
        "canva": "https://www.canva.com",
    }
    
    try:
        if open_match:
            spoken_app = open_match.group(1).strip().strip(".,!?")
            app_cmd = APP_MAPPING.get(spoken_app, spoken_app)
            if "http" in app_cmd:
                webbrowser.open(app_cmd)
                reply = f"Opening {spoken_app}..."
            else:
                try:
                    from AppOpener import open as appopen
                    appopen(spoken_app, match_closest=True)
                except:
                    subprocess.Popen(f"start {app_cmd}", shell=True)
                reply = f"Opening {spoken_app}..."
        elif close_match:
            spoken_app = close_match.group(1).strip().strip(".,!?")
            app_cmd = APP_MAPPING.get(spoken_app, spoken_app)

            # Map web/URL apps to their real process name so we only kill that one
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
                # Fallback: if it's a URL app, kill only its mapped process
                if "http" in app_cmd:
                    proc = WEB_PROCESS_MAP.get(spoken_app.lower(), "chrome.exe")
                    os.system(f"taskkill /f /im {proc}")
                else:
                    os.system(f"taskkill /f /im {app_cmd}.exe")
            reply = f"Closing {spoken_app}..."
        elif search_match:
            query = search_match.group(1).strip().strip(".,!?")
            webbrowser.open(f"https://www.google.com/search?q={query}")
            reply = f"Searching for {query}..."
        else:
            reply = None   # unrecognised command — stay silent
    except Exception as e:
        logger.error(f"Command error: {e}")
        reply = None   # don't spam the chat on errors

    # Only broadcast if there's a real reply
    if reply:
        await manager.broadcast(json.dumps({"type": "chat", "sender": "Jarvis", "text": reply}))
        if core_system and 'voice' in core_system:
            core_system['voice'].speak(reply)

def run_web_server(port=8000, core_ref=None):
    global core_system
    core_system = core_ref
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    
    # Disable signal handling since we are running in a thread
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    
    try:
        # Pass empty list for signals to avoid ValueError in background thread
        asyncio.get_event_loop().run_until_complete(server.serve(sockets=None))
    except Exception as e:
        logger.error(f"Uvicorn error: {e}")

def start_server_in_background(core_ref=None):
    server_thread = threading.Thread(target=run_web_server, args=(8000, core_ref), daemon=True)
    server_thread.start()
