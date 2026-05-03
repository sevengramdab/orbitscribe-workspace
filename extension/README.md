# OrbitScribe Swarm

Agentic swarm chatbot for VS Code — powered by local LLMs (Ollama, LM Studio) and cloud APIs (Gemini).

## Features

- **Ask Mode** — Direct Q&A with your preferred LLM
- **Plan Mode** — Step-by-step implementation planning
- **Agent Mode** — Single specialized agent with tool access
- **Swarm Mode** — Multi-agent parallel collaboration

## Requirements

- [OrbitScribe Swarm Backend](https://github.com/orbstudio/orbitscribe) running on port 58081
- Ollama, LM Studio, or Gemini API key configured

## Setup

1. Start the swarm backend:
   ```bash
   cd swarm-backend
   pip install -r requirements.txt
   python main.py
   ```

2. The extension will auto-detect and connect to `http://127.0.0.1:58081`.

## Commands

| Command | Keybinding |
|---------|-----------|
| Open Swarm Panel | — |
| Voice Input | — |
| Ask / Plan / Agent / Swarm Mode | — |

## Settings

- `orbitscribe.apiMode` — `local_only`, `cloud_only`, or `hybrid`
- `orbitscribe.backendPort` — Backend port (default: 58081)
- `orbitscribe.ollamaUrl` — Ollama URL
- `orbitscribe.lmStudioUrl` — LM Studio URL
