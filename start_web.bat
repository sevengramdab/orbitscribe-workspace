@echo off
REM Voice-to-Text Web GUI Launcher

echo.
echo ================================================
echo  OrbitScribe — Web GUI
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
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing missing dependency: Flask...
    pip install Flask
    if errorlevel 1 (
        echo ERROR: Failed to install Flask.
        echo Run setup.bat as Administrator, then try again.
        pause
        exit /b 1
    )
)

echo Starting server... The browser will open automatically.
echo.
echo If the browser does not open automatically, visit:
echo   http://127.0.0.1:58080
echo.
echo Keep this window open. Press Ctrl+C here to stop.
echo.

python voice_to_text_web.py

REM If python exited with an error, pause so the user can read it
if errorlevel 1 (
    echo.
    echo The server exited with an error.
    pause
)
