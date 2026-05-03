# OrbitScribe

**Voice-first AI coding assistant.** Speak naturally. Let a swarm of agents write, review, test, and document your code — inside VS Code or standalone.

![OrbitScribe](static/favicon.ico)

---

## What is OrbitScribe?

OrbitScribe is a voice-to-text engine with an integrated agent swarm. It has three components that work together:

| Component | What it does |
|-----------|-------------|
| **OrbitScribe Desktop** | Voice-to-text app with STT, TTS, auto-type, clipboard, themes, and docked window modes |
| **VS Code Extension** | Chat panel inside VS Code with Ask / Plan / Agent / Swarm modes |
| **Swarm Backend** | FastAPI service that routes requests to local or cloud LLMs and orchestrates multi-agent collaboration |

---

## Quick Start

### 1. OrbitScribe Desktop

```bash
# Install Python dependencies
pip install speechrecognition pyautogui pyperclip pywebview flask pyttsx3

# Run
python voice_to_text.py
```

Or use the batch files:
- `start.bat` — Normal floating window
- `start_console.bat` — With console visible
- `start_web.bat` — Web-only mode

### 2. Swarm Backend

```bash
cd swarm-backend
pip install -r requirements.txt
python main.py
```

The backend starts on `http://127.0.0.1:58081`.

Configure via environment variables or `.env`:

```env
SWARM_API_MODE=hybrid          # local_only | cloud_only | hybrid
SWARM_PORT=58081
OLLAMA_URL=http://127.0.0.1:11434
LMSTUDIO_URL=http://127.0.0.1:1234
GEMINI_API_KEY=your_key_here
```

### 3. VS Code Extension

```bash
cd extension
npm install
npm run compile
```

Press `F5` in VS Code to launch the Extension Development Host, or package with `vsce package`.

---

## Features

### 🎙️ Voice-to-Text
- Push-to-talk mic with real-time transcription
- Auto-copy to clipboard
- Auto-type into active window with trailing-space fix
- Text-to-Speech with voice selection
- Adjustable mic sensitivity with calibration

### 🎨 Customization
- 5 color themes: Orbit, Neon, Ember, Forest, Sunset
- Custom background images (file picker, `cover` fit)
- Glassmorphism panels with `backdrop-filter: blur`
- Theme and background persistence via `localStorage`

### 🪟 Window Modes
- **Floating** — Free-floating translucent window
- **Dock Left / Dock Right** — Snapped to screen edge with title bar
- **Mass Agent Swarm** — Activates the agent swarm panel

### 🐝 Agent Swarm
The swarm backend runs multiple specialized agents in parallel:

| Agent | Role |
|-------|------|
| **Coder** | Write and modify code |
| **Researcher** | Investigate codebases and documentation |
| **Debugger** | Find and fix bugs |
| **Architect** | System design and planning |
| **Tester** | Write tests and validate edge cases |

Modes:
- **Ask** — Direct Q&A with LLM
- **Plan** — Step-by-step implementation planning
- **Agent** — Autonomous single agent with tool access
- **Swarm** — Multi-agent parallel collaboration with synthesis

### 🔒 API Lockout
Control which LLMs the swarm can access:

- `local_only` — Ollama / LM Studio only (air-gapped)
- `cloud_only` — Gemini / OpenAI / Anthropic only
- `hybrid` — Auto-select based on task complexity

---

## Architecture

```
┌─────────────────┐     Speech / Text      ┌──────────────────┐
│  OrbitScribe    │ ◄────────────────────► │  Swarm Backend   │
│  (pywebview)    │      HTTP/SSE          │  (FastAPI)       │
│                 │                        │  Port 58081      │
└─────────────────┘                        └────────┬─────────┘
        ▲                                           │
        │ VS Code Extension API                     │ HTTP
        │                                           ▼
┌───────┴─────────┐                        ┌──────────────────┐
│  VS Code Ext    │ ◄────────────────────► │  LLM Providers   │
│  (TypeScript)   │   Webview + HTTP       │  Ollama / Gemini │
└─────────────────┘                        └──────────────────┘
```

---

## Project Structure

```
voice to text engine/
├── voice_to_text.py          # Main entry point
├── voice_to_text_web.py      # Flask backend (STT, TTS, settings)
├── voice_to_text_docked.py   # Docked window launcher
├── voice_to_text_console.py  # Console version
├── templates/
│   └── index.html            # OrbitScribe UI (splash, mic, panels, swarm)
├── static/
│   └── favicon.ico           # Orbital logo
├── extension/                # VS Code Extension
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── extension.ts      # Extension lifecycle, commands, tree views
│       ├── panels/
│       │   └── SwarmPanel.ts # Webview panel with chat UI
│       └── services/
│           └── BackendService.ts # Backend lifecycle management
├── swarm-backend/            # FastAPI Agent Swarm
│   ├── main.py               # Entry point
│   ├── requirements.txt
│   ├── api/
│   │   └── routes.py         # REST + SSE endpoints
│   ├── core/
│   │   ├── config.py         # Settings & API mode lockout
│   │   └── model_router.py   # LLM routing (Ollama/LMStudio/Gemini)
│   ├── agents/
│   │   ├── base.py           # Agent definitions
│   │   └── swarm_orchestrator.py # Multi-agent coordination
│   └── modes/
│       ├── ask_mode.py
│       ├── plan_mode.py
│       ├── agent_mode.py
│       └── swarm_mode.py
```

---

## Voice-to-Swarm Bridge

When **Mass Agent Swarm** is activated in OrbitScribe:

1. The swarm panel appears in the UI
2. Every voice transcription is automatically sent to `POST /api/swarm`
3. Agents run in parallel and stream results back
4. Results display with agent badges, status, and synthesized output

You can also close the swarm panel at any time to return to normal voice-to-text mode.

---

## Requirements

### OrbitScribe Desktop
- Python 3.10+
- Windows (uses `ctypes` for window management)
- Microphone
- Speakers (for TTS)

### Swarm Backend
- Python 3.10+
- `fastapi`, `uvicorn`, `aiohttp`

### LLM Providers (at least one)
- **Ollama** — Local models (recommended: `qwen2.5-coder`)
- **LM Studio** — Local OpenAI-compatible server
- **Gemini** — Google API (set `GEMINI_API_KEY`)

### VS Code Extension
- Node.js 18+
- VS Code 1.80+

---

## Development

### Run the backend in development
```bash
cd swarm-backend
python main.py
```

### Compile the extension
```bash
cd extension
npm run compile
# or watch mode
npm run watch
```

### Run OrbitScribe with console
```bash
python voice_to_text_console.py
```

---

## License

MIT
