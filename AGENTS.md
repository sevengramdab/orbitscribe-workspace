# Agent Instructions for OrbitScribe

## Reload & Continue Workflow

When you are working on a task and need to reload VS Code: to test changes, update the extension, or apply configuration changes, **do not ask the user for permission to reload**. Instead, use the built-in reload-and-continue command:

```bash
reload-and-continue "<what you are currently doing>"
```

Examples:
```bash
reload-and-continue "Test the navbar fix I just applied and continue styling the dropdown"
reload-and-continue "Verify the backend starts after the dependency changes and continue integration"
reload-and-continue "Check that the new keybinding works and continue polishing the UI"
```

### What happens automatically
1. Your context message is saved
2. VS Code: Extension Host restarts
3. After ~40 seconds, the OrbitScribe extension detects the reload
4. The terminal opens automatically
5. `kimi -r <session>` restores your CLI session
6. Your context message is sent so you continue exactly where you left off

### Crash Recovery (Extension Host Crashes)
If VS Code: shows "Extension Host Terminated Unexpectedly" (or the Kimi panel shows "lost connection to process"), the system now auto-recovers:

1. **Extension-side detection**: On the next extension host start, OrbitScribe detects the stale heartbeat file and triggers terminal auto-resume automatically — even if the crash happened hours ago (within a 30-minute recovery window).
2. **Stale lock cleanup**: Crash survivors (`.reload-resume-lock` files left behind because `deactivate()` never ran) are automatically cleaned on every extension activation.
3. **External watchdog fallback**: A lightweight Python daemon (`tools/resume_watchdog.py`) monitors the heartbeat. If the extension host stays down but VS Code: is still running, the daemon opens the terminal and types the resume command for you.

### Important notes
- The terminal panel is the primary resume target (reliable). The webview is restored as a best-effort fallback.
- After reload or crash recovery, check the Terminal panel at the bottom for your resumed session.
- If something goes wrong, check:
  - `auto_resume_watcher.log` — legacy pyautogui-based watcher
  - `tools/resume_watchdog.log` — external safety-net daemon
  - `screenshots/` — visual debug output

## Project Structure
- `extension/` - VS Code: extension source (TypeScript)
- `swarm-backend/` - FastAPI backend for multi-agent orchestration
- `tools/` - Automation scripts including auto-resume
- `voice_to_text.py` / `voice_to_text_*.py` - Desktop STT/TTS app

## Coding Conventions
- Python: PEP 8, type hints where helpful
- TypeScript: strict mode, async/await for I/O
- Backend port: 58081
