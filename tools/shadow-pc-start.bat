@echo off
setlocal
set "SHADOW_DIR=%USERPROFILE%\simplepod-shadow"
set "SIMPOD_PORT=8002"
set "PYTHONPATH=%SHADOW_DIR%"

if not exist "%SHADOW_DIR%\.git" (
    echo [shadow] Repo not found. Cloning...
    cd /d "%USERPROFILE%"
    git clone https://github.com/sevengramdab/swarm-backend.git simplepod-shadow
    if errorlevel 1 (
        echo [shadow] Clone failed.
        pause
        exit /b 1
    )
) else (
    echo [shadow] Pulling latest...
    cd /d "%SHADOW_DIR%"
    git pull
)

cd /d "%SHADOW_DIR%"
if not exist ".venv\Scripts\activate.bat" (
    echo [shadow] Creating venv...
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)

call .venv\Scripts\activate.bat
set SIMPOD_PORT=8002
set PYTHONPATH=%SHADOW_DIR%
echo [shadow] Starting shadow_node.py on port %SIMPOD_PORT%...
python shadow_node.py
