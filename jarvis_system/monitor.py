import psutil
import platform
import logging
import subprocess
import ctypes
import os

logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self):
        self.os_name = platform.system()

    def get_cpu_usage(self):
        return psutil.cpu_percent(interval=0.1)

    def get_ram_usage(self):
        ram = psutil.virtual_memory()
        return ram.percent

    def get_battery(self):
        if not hasattr(psutil, "sensors_battery"):
            return None
        battery = psutil.sensors_battery()
        if battery:
            return {"percent": battery.percent, "plugged": battery.power_plugged}
        return None

    def lock_workstation(self):
        """Locks the Windows workstation."""
        if self.os_name == "Windows":
            ctypes.windll.user32.LockWorkStation()
            return True
        return False

    def sleep_workstation(self):
        """Puts Windows to sleep."""
        if self.os_name == "Windows":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return True
        return False
        
    def change_volume(self, direction):
        """Increases or decreases volume using powershell as fallback"""
        if self.os_name == "Windows":
            # Using simple powershell fallback. For robust use pycaw or keyboard
            try:
                import keyboard
                if direction == "up":
                    for _ in range(5): keyboard.send("volume up")
                elif direction == "down":
                    for _ in range(5): keyboard.send("volume down")
                elif direction == "mute":
                    keyboard.send("volume mute")
                return True
            except ImportError:
                logger.error("keyboard library missing for volume control")
        return False

    def check_running_apps(self, app_name):
        """Check if an application is running."""
        app_name = app_name.lower()
        if not app_name.endswith('.exe'):
            app_name += '.exe'
            
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == app_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def execute_automation_mode(self, mode_name):
        """Executes predefined routines."""
        mode_name = mode_name.lower()
        if "coding" in mode_name:
            # Example: open VS Code, Chrome
            subprocess.Popen("code", shell=True)
            subprocess.Popen("start chrome", shell=True)
            return "Activated coding mode. Opening VS Code and Chrome."
        elif "gaming" in mode_name:
            # Example: Close background apps like Chrome or Spotify to free RAM
            os.system("taskkill /f /im chrome.exe")
            return "Activated gaming mode. Closed browser to free up memory."
            
        return f"Automation mode '{mode_name}' is not recognized."
