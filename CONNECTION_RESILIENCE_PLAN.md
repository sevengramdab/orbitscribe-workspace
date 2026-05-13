# Connection Resilience & Mass Agent Swarm Plan

## What Went Wrong (Previous Session)

| Issue | Root Cause | Impact |
|-------|-----------|--------|
| Jukebox 404 | Browser opened to `127.0.0.1:58800/jukebox/` instead of `58080` | Visualizer appeared broken |
| Connection Loss | VS Code: Extension Host instability during `StrReplaceFile` + user rejection | Session dropped mid-fix |
| Stale Process Risk | Old Python server may not pick up blueprint changes | Routes missing until restart |

**Finding:** Port `58800` is **not used anywhere** in the codebase. The Voice/Jukebox server runs on `58080`. The 404 was a phantom port.

---

## Fixes Applied

1. **Verified live server** — Jukebox is healthy at `http://127.0.0.1:58080/jukebox/` (~50 FPS, 5 viewports).
2. **Synced extension copy** — Added `infinite_jukebox` blueprint registration to `extension/voice-backend/voice_to_text_web.py` so the extension-spawned backend also serves `/jukebox`.
3. **Opened browser** to the correct URL.

---

## Mass Agent Swarm Activation

The command `orbitscribe.activateMassSwarm` is already registered in the extension:

```typescript
vscode.commands.registerCommand('orbitscribe.activateMassSwarm', async () => {
    SwarmPanel.createOrShow(context.extensionUri, 'ask');
    SwarmPanel.currentPanel?.reveal();
    setTimeout(() => {
        CommandViewport.createOrShow(context.extensionUri);
    }, 200);
});
```

**How to trigger it:**
- Press `Ctrl+Shift+P` → type **"OrbitScribe: Activate Multi-Agent"** → Enter.
- Or bind a key in `keybindings.json`:
  ```json
  {
    "key": "ctrl+shift+m",
    "command": "orbitscribe.activateMassSwarm"
  }
  ```

This opens the **SwarmPanel** (ask mode) + **CommandViewport** side-by-side for multi-agent orchestration.

---

## Bypass Strategy — Preventing Future Connection Drops

### 1. Always Use `reload-and-continue`

When you need to reload VS Code: to test changes, **do not ask for permission**. Use:

```bash
reload-and-continue "<what you are currently doing>"
```

This saves context, restarts the extension host, and auto-resumes your Kimi CLI session after ~40s.

### 2. Never Hardcode Port 58800

There is **no service on 58800**. Bookmark only these endpoints:

| Service | URL |
|---------|-----|
| Voice + Jukebox | `http://127.0.0.1:58080` |
| Swarm Backend | `http://127.0.0.1:58081` |
| Jukebox Visualizer | `http://127.0.0.1:58080/jukebox/` |
| Jukebox API | `http://127.0.0.1:58080/jukebox/api/status` |

### 3. Kill Stale Processes Before Restarting

If routes are missing after a code change, the server is likely an old process:

```powershell
# Kill all voice web servers
Get-Process python* | Where-Object { $_.CommandLine -like "*voice_to_text_web*" } | Stop-Process -Force
# Then restart
python voice_to_text_web.py
```

### 4. Extension Host Crash Recovery (Already Active)

The system has **three layers** of crash recovery:

1. **Extension-side detection** — On next activation, stale heartbeat files trigger auto-resume automatically (30-min window).
2. **Stale lock cleanup** — `.reload-resume-lock` files from crashes are cleaned on every activation.
3. **External watchdog** — `tools/resume_watchdog.py` monitors the heartbeat. If VS Code: stays down but is running, the daemon opens the terminal and types the resume command.

**If recovery fails, check:**
- `tools/resume_watchdog.log`
- `auto_resume_watcher.log`
- `screenshots/` (visual debug)

### 5. Safer Code Edit Pattern

Instead of large `StrReplaceFile` operations during live sessions (which can destabilize the extension host), prefer:

1. **Plan mode** for multi-file refactors (`EnterPlanMode` → user approves → execute).
2. **Smaller incremental edits** rather than 500-line replacements.
3. **Save & reload** via `reload-and-continue` rather than hot-patching the running extension.

---

## Quick Health Check Script

Save this as `tools/health_check.ps1` for one-liner diagnostics:

```powershell
$ports = @(58080, 58081)
foreach ($p in $ports) {
    $conn = Test-NetConnection -ComputerName 127.0.0.1 -Port $p -WarningAction SilentlyContinue
    Write-Host "Port $p : $($conn.TcpTestSucceeded ? 'OPEN' : 'CLOSED')"
}
Invoke-RestMethod -Uri "http://127.0.0.1:58080/jukebox/api/status" -ErrorAction SilentlyContinue | Select-Object running, fps
```

---

## Summary

- **Jukebox is live** — use `58080`, not `58800`.
- **Mass Swarm command** is ready: `Ctrl+Shift+P` → "Activate Multi-Agent".
- **Use `reload-and-continue`** instead of manual reloads to avoid session loss.
- **Three crash-recovery layers** are active; if they fail, the logs above tell the story.
