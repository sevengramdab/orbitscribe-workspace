# OrbitScribe — Rock-Solid Resilience Report

**Date:** 2026-05-27
**Branch:** master
**Commits:** `fbb6f8e`, `17a4099`, `61310b6`

---

## Executive Summary

The OrbitScribe swarm backend, VS Code: extension, and Rust AOE supervisor were hardened against the most common production failure modes on Windows:

| Failure Mode | Before | After |
|-------------|--------|-------|
| Rust AOE won't compile | `link.exe` missing, build impossible | VS Build Tools 2022 installed, release binary builds in 81s |
| Docker Desktop down | AOE binary crashes on startup | Boots in "degraded" mode, HTTP 503 on Docker ops, `/health` reports `docker_available: false` |
| Stale python.exe on port 58081 | Backend fails to start, cryptic error | Auto-detected, stale process killed, port reclaimed automatically |
| Foreign process on 58081 | Complete failure | Scans 58082–58091, picks free port, persists to config |
| Extension webviews | All hardcoded `58081` | Read dynamic port from config, follow backend wherever it lands |
| AOE supervisor missing | Backend auto-mode blocks on subprocess | Async client with 3-attempt retry, auto-starts supervisor, 15s health probe |
| Backend crash on startup | "Failed within 15 seconds" | Stderr captured, specific error extracted (port conflict, missing module) |
| Port 58082 conflict (AOE) | No handling | Retry logic in `aoe_mesh.py`, configurable via `AOE_PORT` env var |

---

## 1. Rust AOE Supervisor — Windows Compilation

### Problem
`cargo build` failed with `link.exe not found`. The MSVC toolchain was completely missing.

### Solution
- Downloaded and installed **Visual Studio Build Tools 2022** with C++ workload (`Microsoft.VisualStudio.Workload.VCTools`)
- Fixed 6 compilation errors in `src/docker.rs` caused by `bollard` API mismatches:
  - `LogOutput` enum uses **struct variants** (`StdOut { message }`) not tuple variants
  - `wait_container()` returns a `Stream`, not a `Future` — cannot `.await`
  - `ListContainersOptions.filters` expects `HashMap<String, Vec<String>>`, not `serde_json::Value`
  - `cpu_usage.total_usage` is `u64`, not `Option<u64>` — `.unwrap_or()` invalid
  - `id: String` moved into async closure — needed clone before spawn
- Added missing `futures` crate to `Cargo.toml`
- Cleared broken `rust-lld` linker config from `.cargo/config.toml`

### Verification
```powershell
cd aoe/supervisor
cargo build --release    # Finished in 81s, 0 errors, 0 warnings
.\target\release\aoe.exe --help
# Agent of Empires — Rust supervisor for the aquaculture mesh
```

---

## 2. Rust AOE Supervisor — Docker Resilience

### Problem
`DockerManager::new()` called `docker.ping().await` on startup. If Docker Desktop was down, the entire binary crashed with:
```
Error: Docker daemon did not respond to ping
```

### Solution
Rewrote `docker.rs` with **lazy connection architecture**:
- `DockerManager::new()` never fails — stores `Option<Docker>` + `docker_available` flag
- `ensure_docker()` tries to connect on every operation; auto-reconnects if Docker comes back
- Added `docker_available: bool` and `last_error: Option<String>` to `MeshStatus`
- Updated `http.rs` endpoints to return HTTP 503 when Docker is unavailable
- `stop()` wipes in-memory state even if Docker daemon is gone

### Verification
```powershell
# With Docker Desktop OFF
.\target\release\aoe.exe --port 58083
# INFO  aoe: AOE supervisor booting port=58083
# WARN  aoe::docker: Docker not available — supervisor will run in degraded mode
# INFO  aoe::http: AOE supervisor listening addr=0.0.0.0:58083

GET http://localhost:58083/health
# {"status":"degraded","docker_available":false,"version":"0.1.0"}

POST http://localhost:58083/mesh/start
# Status: 503
# {"success":false,"error":"failed to start mesh: Docker daemon did not respond to ping"}

POST http://localhost:58083/mesh/stop
# {"success":true,"data":{"wiped":true}}
```

---

## 3. Backend Launcher — Port-Conflict Auto-Recovery

### Problem
Stale `python.exe` processes frequently held port 58081 after crashes or reloads. The extension would try to start a new backend, get `WinError 10048`, and fail with a generic timeout.

### Solution — Three launchers updated

#### TypeScript (`extension/src/services/BackendService.ts`)
- `isPortInUse(port)` — binds a temp TCP socket to test availability
- `killProcessOnPort(port)` — runs `netstat -ano`, identifies Python PIDs, `taskkill /F`
- `findFreePort(startPort)` — linear scan over 10 ports
- `resolvePortConflict()` — kills stale Python backends first; if foreign process, scans for fallback
- Persists resolved port to VS Code: workspace config (`orbitscribe.backendPort`)

#### PowerShell (`tools/start-swarm-backend.ps1`)
- `Test-PortInUse` — `[System.Net.Sockets.TcpListener]` probe
- `Get-StalePythonPid` — `netstat` → `tasklist` CSV parsing
- `Find-FreePort` — scans range, returns first free port

#### Python (`launch.py`)
- `is_port_in_use(port)` — `socket.connect_ex()` probe
- `kill_stale_python_on_port(port)` — `netstat` / `lsof` + `taskkill` / `kill -9`
- `find_free_port(startPort)` — scans range
- `resolve_port(port)` — kills stale → fallback scan → exits if nothing free
- Passes `SWARM_PORT` environment variable to backend process

---

## 4. Extension Webviews — Dynamic Port

### Problem
Every webview panel hardcoded `http://127.0.0.1:58081`. If the backend port conflict resolver shifted to 58082, the entire UI broke silently.

### Files Fixed
| File | Approach |
|------|----------|
| `OrbitScribeSidebarProvider.ts` | Injects `<script>const API_BASE = 'http://127.0.0.1:PORT';</script>` into webview HTML; all `fetch()` calls use `API_BASE` |
| `SwarmPanel.ts` | Reads `backendPort` from VS Code: config at top of message handler |
| `CommandViewport.ts` | Same config read |
| `extension.ts` | Same config read |
| `CommandDeckPanel.ts` | Reads file from disk, string-replaces `127.0.0.1:58081` with dynamic port before serving |

---

## 5. Backend ↔ AOE Supervisor Integration

### Problem
`modes/auto_mode.py` dispatched to AOE via blocking `subprocess.run()` calls with no retry, no health check, and no graceful fallback.

### Solution
- **New module:** `core/aoe_client.py` — async `httpx` client
  - 3-attempt retry with 1s exponential backoff
  - `ensure_supervisor(max_wait=15.0)` — polls `/health` until online
  - Methods: `health()`, `mesh_status()`, `mesh_start()`, `mesh_stop()`, `mesh_failsafe()`, `mesh_logs()`
- **Updated:** `modes/auto_mode.py`
  - Checks supervisor health via async client
  - If offline, auto-starts via `tools/aoe.ps1 start`
  - Polls for 15 seconds; streams SSE status events throughout
- **Updated:** `tools/aoe_mesh.py`
  - Retry logic on all HTTP calls
  - `AOE_PORT` environment variable override
- **Updated:** `tools/aoe_supervisor.py` (Python shim)
  - `/health` returns JSON matching Rust API: `{"status", "docker_available", "version"}`

---

## 6. Startup Health Probe

### Problem
Backend spawn waited 15s polling health, but if the process crashed immediately (e.g. port in use), the user got a useless timeout message.

### Solution
- Added 20-line **stderr ring buffer** during startup
- Checks `this.process === null` during health poll → process crashed
- Parses stderr for known errors:
  - `"Address already in use"` → specific port-conflict error
  - `"ModuleNotFoundError"` → missing dependency error
  - Other → full stderr dump

---

## Test Results

### Dev backend (`swarm-backend/`)
```
45 passed in 4.10s
```

### Bundled backend (`extension/swarm-backend/`)
```
45 passed in 3.99s
```

### TypeScript extension
```
> tsc -p ./
# 0 errors, 0 warnings
```

### Rust AOE supervisor
```
cargo build --release
# Finished `release` profile [optimized] target(s) in 81s
# 0 errors, 0 warnings
```

---

## Known Limitations

1. **Docker Desktop requires admin fix.** WSL2 has zero installed distributions. Run as Administrator:
   ```powershell
   wsl --install -d Ubuntu
   ```
   Then reboot and start Docker Desktop. Until then, the Rust AOE supervisor runs in degraded mode and the Python shim is the working fallback.

2. **Voice backend (port 58080)** and **discovery service (port 58082)** do not yet have port-conflict auto-recovery. These are lower priority because they are auxiliary services.

---

## Commits

| Commit | Description |
|--------|-------------|
| `fbb6f8e` | Fix Rust AOE supervisor compilation on Windows |
| `17a4099` | Rock-solid AOE supervisor + backend launcher resilience |
| `61310b6` | Make extension webviews resilient to dynamic backend ports |
