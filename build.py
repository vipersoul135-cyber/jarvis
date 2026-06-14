import os
import subprocess

def build():
    print("Building JARVIS Executable...")
    # --noconsole hides the background terminal so only the PyQt6 GUI shows
    cmd = [
        "pyinstaller",
        "--name=JARVIS",
        "--windowed", 
        "--noconsole",
        "--icon=NONE",  # Add a path to a .ico file here if you have one
        "main.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("Build completed successfully! You can find JARVIS.exe in the 'dist' folder.")
    except Exception as e:
        print(f"Build failed: {e}")

if __name__ == "__main__":
    build()
