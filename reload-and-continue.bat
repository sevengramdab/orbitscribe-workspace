@echo off
REM Reload VS Code: and auto-resume Kimi session with context.
REM Usage: reload-and-continue "Test the changes and continue debugging"

cd /d "%~dp0"
python tools\reload_with_resume.py %*
