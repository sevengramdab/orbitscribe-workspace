@echo off
REM Voice-to-Text Setup Script
REM Installs all required Python packages

echo ================================================
echo  Voice-to-Text Tool - Dependency Installer
echo ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8 or newer from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found.
echo.
echo Installing required packages...
echo This may take a few minutes.
echo.

pip install --upgrade pip
pip install SpeechRecognition PyAudio pyperclip pyautogui keyboard Flask pyttsx3 pywebview

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed.
    echo If PyAudio fails, you may need to install it manually:
    echo   pip install pipwin
    echo   pipwin install pyaudio
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================
echo  Installation complete!
echo ================================================
echo.
echo To start the tool, run:
echo   python voice_to_text.py       (global hotkey version)
echo   python voice_to_text_console.py (console version)
echo   python voice_to_text_web.py     (browser GUI version)
echo   python voice_to_text_float.py   (floating window version)
echo.
pause
