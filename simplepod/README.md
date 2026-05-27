# SimplePod 🛰️

Peer-to-peer remote control for two computers. Run it on both machines — they auto-discover each other via UDP broadcast and either side can control the other.

## Quick Start

### On both computers
```bash
# Install dependencies
pip install -r requirements.txt

# Run with default settings
python run.py
```

### Packaging as a standalone executable
```bash
# Build a single .exe with PyInstaller
python build_exe.bat
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SIMPLEPOD_ROLE` | `shadow` | `shadow` (remote/cloud PC) or `local` (your physical PC) |
| `SIMPLEPOD_NODE_NAME` | hostname | Display name in the UI |
| `SIMPLEPOD_API_PORT` | `58091` | HTTP control API port |
| `SIMPLEPOD_DISCOVERY_PORT` | `58090` | UDP broadcast discovery port |
| `SIMPLEPOD_TOKEN` | `simplepod-default-token` | Auth token (must match on both sides) |
| `STREAMLIT_SERVER_PORT` | `8501` | Streamlit web UI port |

### Typical setup

**Shadow PC** (cloud/remote):
```bash
set SIMPLEPOD_ROLE=shadow
set SIMPLEPOD_NODE_NAME=ShadowPC
python run.py
```

**Local PC** (your laptop):
```bash
set SIMPLEPOD_ROLE=local
set SIMPLEPOD_NODE_NAME=LocalPC
python run.py
```

Open `http://localhost:8501` on both machines. They will discover each other within ~3 seconds.

## Features

- 🔍 **Auto-discovery** — UDP broadcast finds peers on the same LAN automatically
- 🔗 **Auto-connect** — Optionally connects to the first peer found
- 📊 **Remote status** — CPU, memory, disk, platform info
- 🖥️ **Command execution** — Run shell commands on the remote peer
- 🔧 **Setup scripts** — Send and run bootstrap scripts
- 📁 **File transfer** — Upload files to the remote peer
- 🔒 **Token auth** — Simple shared-token authentication
- 💓 **Heartbeat monitoring** — Real-time health check with latency display
- 📸 **Remote screenshot** — Capture and view remote desktop instantly
- 📂 **Bidirectional file manager** — List, download, and delete remote files
- 📦 **Standalone executable** — Package everything into a single .exe with PyInstaller

## Building

SimplePod can be packaged into a standalone Windows executable using PyInstaller. This removes the need for a Python installation on the target machine.

```bash
python build_exe.bat
```

The script runs:
```
pyinstaller --onefile --name simplepod run.py
```

Requirements:
- `pip install pyinstaller` (included in `requirements.txt`)
- The resulting `dist/simplepod.exe` bundles the Python runtime, all dependencies, and the application code into a single file.

## Architecture

```
┌──────────────┐                      ┌──────────────┐
│   Local PC   │  ◄── UDP 58090 ──►   │  Shadow PC   │
│  Streamlit   │                      │  Streamlit   │
│   UI :8501   │  ◄── HTTP 58091 ──►  │   UI :8501   │
│  FastAPI API │                      │  FastAPI API │
└──────────────┘                      └──────────────┘
```

Both sides run the same code. Either can initiate control.
