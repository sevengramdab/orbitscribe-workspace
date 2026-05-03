@echo off
REM Voice-to-Text Floating Window Launcher

echo.
echo ================================================
echo  OrbitScribe — Floating Window
echo ================================================
echo.

REM Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Quick dependency check
python -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo Installing missing dependency: pywebview...
    pip install pywebview
    if errorlevel 1 (
        echo ERROR: Failed to install pywebview.
        echo Run setup.bat as Administrator, then try again.
        pause
        exit /b 1
    )
)

echo Opening a phone-sized floating window that stays on top...
echo.
echo Keep this window open. Press Ctrl+C here to stop.
echo.

python voice_to_text_float.py

REM If python exited with an error, pause so the user can read it
if errorlevel 1 (
    echo.
    echo The app exited with an error.
    pause
)
