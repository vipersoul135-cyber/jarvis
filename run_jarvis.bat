@echo off
title Ultimate JARVIS Assistant Launcher
echo ===================================================
echo   Starting Ultimate JARVIS Assistant...
echo ===================================================
echo.

cd /d "%~dp0"

echo [INFO] Booting Main System...
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] JARVIS crashed or failed to start.
    echo Make sure you have installed the requirements: python -m pip install -r requirements.txt
    pause
)
