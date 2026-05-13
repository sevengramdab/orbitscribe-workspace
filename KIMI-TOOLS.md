# Kimi Code Tools for OrbitScribe

> **For Kimi Code agents:** This file contains reusable commands and scripts for working on OrbitScribe.

---

## Reload VS Code: Without Losing Context

### ✅ Working Method: Restart Extension Host

```powershell
powershell -ExecutionPolicy Bypass -File tools\reload-vscode.ps1
```

This sends **`Developer: Restart Extension Host`**. It restarts the extension host while **preserving the integrated terminal and Kimi session**.

**Verified working:** Terminal survived, extension reloaded with new code, Mass Agent Swarm activated successfully.

**Parameters:**
- `-WindowTitleSubstring "OrbitScribe"` — match a specific window title
- `-PreDelayMs 1200` — longer delay before sending keys
- `-FullReload` — use `Developer: Reload Window` instead (kills terminals, safety-net will auto-resume Kimi)

### How it works
1. Saves current Kimi session ID
2. Spawns a **WMI-detached safety-net process** (survives VS Code: reload) as backup
3. Sends `Developer: Restart Extension Host` to VS Code:
4. Terminal stays alive → conversation continues seamlessly
5. If terminal dies (rare), safety-net waits 20s and auto-resumes Kimi

### ⚠️ Avoid Full Reload
`Developer: Reload Window` kills terminals. Only use `-FullReload` if Extension Host restart doesn't pick up changes. The safety-net will recover Kimi, but there will be a ~20s gap.

---

## Updating Extension Files

```powershell
cd extension; npm run compile
```

Then copy to installed extension:
```powershell
$extDir = "$env:USERPROFILE\.vscode\extensions\orbstudio.orbitscribe-swarm-1.0.2"
Rename-Item "$extDir\out" "$extDir\out-old" -Force -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force extension\out "$extDir\out"
```

Then run `reload-vscode.ps1` to restart the extension host.

---

## Start the Swarm Backend

```powershell
Start-Process -FilePath "python" -ArgumentList "swarm-backend\main.py" -WorkingDirectory (Get-Location) -WindowStyle Hidden
```

---

## Test Mass Agent Swarm (Backend API)

```powershell
$body = @{
    message = "Activate mass agent swarm for this project."
    mode = "swarm"
    workspace_context = "Project: voice to text engine"
    autonomy_level = "default"
    temperature = 0.7
    model = "llama3:latest"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://127.0.0.1:58081/api/chat -Method POST -Body $body -ContentType 'application/json' -TimeoutSec 10
```

Expected: `🐝 **Swarm Activated**` followed by Phase 1 approval gate.

---

## Health Checks

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:58081/api/health -Method GET
Invoke-RestMethod -Uri http://127.0.0.1:11434/api/tags -Method GET
```

---

## Extension Paths

- **Built output:** `extension/out/`
- **Installed:** `%USERPROFILE%\.vscode\extensions\orbstudio.orbitscribe-swarm-1.0.2\`
- **Backend:** `%USERPROFILE%\.vscode\extensions\orbstudio.orbitscribe-swarm-1.0.2\swarm-backend\`

If backend fails with "main.py not found":
```powershell
robocopy swarm-backend "$env:USERPROFILE\.vscode\extensions\orbstudio.orbitscribe-swarm-1.0.2\swarm-backend" /E
```

---

## What Was Fixed

1. **Mass Agent Swarm button** — auto-sends activation text
2. **File watcher removed** — no more reload loops
3. **Activation event** added for `orbitscribe.activateMassSwarm`
4. **Backend files** copied to installed extension
5. **Reload script** — preserves Kimi session via `Restart Extension Host`
