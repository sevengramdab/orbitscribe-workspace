# Voice-to-Text Tool

A simple, free voice-to-text tool for Windows that transcribes your speech and either copies it to the clipboard or types it directly into any text field — including Copilot Chat, Discord, VS Code, browser chat boxes, etc.

## Features

- **Global hotkey** (`Ctrl+Alt+V`) works from anywhere
- **Auto-clipboard** — transcribed text is instantly copied
- **Auto-type** — text is typed directly into the focused input field
- **Free** — uses Google Speech Recognition (internet required)
- **No API keys** needed

## Quick Start

### 1. Install dependencies

Double-click `setup.bat`, or run in Command Prompt / PowerShell:

```bash
pip install SpeechRecognition PyAudio pyperclip pyautogui keyboard Flask
```

> **Note:** PyAudio sometimes fails to install via pip. If it does, run:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

### 2. Run the tool

**Web GUI (recommended)** — runs in your browser with a clean interface:
```bash
python voice_to_text_web.py
```
Or double-click `start_web.bat`.

**Global hotkey** — press `Ctrl+Alt+V` from anywhere:
```bash
python voice_to_text.py
```
Or double-click `start.bat`.

**Console** — simple text-based version:
```bash
python voice_to_text_console.py
```

### 3. Use it

1. Click inside any chat box (Copilot Chat, browser, Discord, etc.)
2. Press **`Ctrl+Alt+V`**
3. Speak clearly
4. Release the keys — your text appears in the chat box automatically

The transcribed text is also copied to your clipboard, so you can paste it anywhere with `Ctrl+V`.

## Admin Rights

The global hotkey (`Ctrl+Alt+V`) requires the script to run **as Administrator** on Windows if you are typing into another elevated window. For most chat apps and browsers, running normally is fine.

If you cannot run as admin, use the console version instead:

```bash
python voice_to_text_console.py
```

This version prompts you to press `Enter` to record instead of using a global hotkey.

## Customization

Open `voice_to_text.py` in any text editor and change these values near the top:

| Setting | Default | Description |
|---------|---------|-------------|
| `HOTKEY` | `"ctrl+alt+v"` | Key combo to trigger recording |
| `AUTO_TYPE` | `True` | Automatically type text into focused field |
| `TIMEOUT_SECONDS` | `30` | Max seconds to listen per utterance |
| `ENERGY_THRESHOLD` | `300` | Microphone sensitivity (lower = more sensitive) |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Microphone error" | Make sure your mic is connected and not used by another app |
| "Could not understand audio" | Speak more clearly, closer to the mic, or reduce background noise |
| Hotkey doesn't work | Run the script as Administrator |
| Hotkey works but types gibberish | The target app may be catching keystrokes differently; use Ctrl+V paste instead |

## Files

| File | Description |
|------|-------------|
| `voice_to_text_web.py` | **Web GUI** — runs in your browser |
| `voice_to_text.py` | Main app with global hotkey |
| `voice_to_text_console.py` | Console version (no admin needed) |
| `setup.bat` | One-click dependency installer |
| `start_web.bat` | Launch the browser GUI |
| `start.bat` | Launch the hotkey version |
| `README.md` | This file |
