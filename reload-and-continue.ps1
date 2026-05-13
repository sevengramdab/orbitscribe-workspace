# Reload VS Code: and auto-resume Kimi session with context.
# Usage: reload-and-continue "Test the changes and continue debugging"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& python "$scriptDir\tools\reload_with_resume.py" @args
