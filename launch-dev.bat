@echo off
chcp 65001 >nul
echo ============================================
echo   ORBITSCRIBE DEV LAUNCHER
echo ============================================
echo.
echo This will:
echo   1. Start Ollama (if not running)
echo   2. Start Swarm Backend (if not running)
echo   3. Launch VS Code: Extension Development Host
echo.

python "%~dp0launch.py" --run

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Dev launcher failed with code %errorlevel%
    pause
)
