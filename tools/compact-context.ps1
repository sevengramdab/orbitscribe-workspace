# compact-context.ps1
# Compacts conversation context for Kimi Code: and OrbitScribe.
# This frees up token/memory by summarizing and truncating long contexts.
# NO RELOAD. Just compacts.

param(
    [string]$WindowTitleSubstring = "Visual Studio Code",
    [switch]$KimiOnly,
    [switch]$OrbitScribeOnly
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class User32Compact {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);
    public const int SW_RESTORE = 9;
}
"@

# ── Find VS Code: ──────────────────────────────────────────────────
$proc = Get-Process -Name "Code" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$WindowTitleSubstring*"
} | Select-Object -First 1

if (-not $proc) {
    $proc = Get-Process -Name "Code" -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowHandle -ne 0
    } | Select-Object -First 1
}

function Focus-VSCode {
    param([IntPtr]$hWnd)
    if ([User32Compact]::IsIconic($hWnd)) {
        [void][User32Compact]::ShowWindowAsync($hWnd, [User32Compact]::SW_RESTORE)
        Start-Sleep -Milliseconds 300
    }
    [void][User32Compact]::SetForegroundWindow($hWnd)
    Start-Sleep -Milliseconds 600
}

# ── Compact Kimi Code: ─────────────────────────────────────────────
if (-not $OrbitScribeOnly) {
    Write-Host "Compacting Kimi Code: context..." -ForegroundColor Cyan
    if ($proc) {
        Focus-VSCode $proc.MainWindowHandle
        [System.Windows.Forms.SendKeys]::SendWait("^l")
        Start-Sleep -Milliseconds 400
        [System.Windows.Forms.SendKeys]::SendWait("/compact")
        Start-Sleep -Milliseconds 300
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
        Write-Host "✅ Kimi Code: /compact sent." -ForegroundColor Green
    } else {
        Write-Warning "VS Code: not found. Skipping Kimi compact."
    }
}

# ── Compact OrbitScribe ────────────────────────────────────────────
if (-not $KimiOnly) {
    Write-Host "Compacting OrbitScribe context..." -ForegroundColor Cyan
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:58081/api/compact" -Method POST `
            -Body '{"session_id":"default","summary":""}' -ContentType 'application/json' -TimeoutSec 5
        if ($resp.ok) {
            Write-Host "✅ OrbitScribe backend compacted ($($resp.old_message_count) → $($resp.new_message_count) messages)" -ForegroundColor Green
        } else {
            Write-Warning "Compact returned: $($resp.error)"
        }
    } catch {
        Write-Warning "OrbitScribe backend not reachable. Start it with: tools\start-swarm-backend.ps1"
    }
}

Write-Host "Context compaction complete." -ForegroundColor Green
