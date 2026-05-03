@echo off
chcp 65001 >nul
echo ============================================
echo   ORBITSCRIBE AUTO-LAUNCHER
echo ============================================
echo.

python "%~dp0launch.py" %*

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Launcher failed with code %errorlevel%
    pause
)
