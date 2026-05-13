# resume-kimi.ps1
# Hardened safety-net resume for Kimi Code: after VS Code: reload.
# Waits for extension auto-resume first, then falls back to SendKeys if needed.

param(
    [string]$WindowTitleSubstring = "Visual Studio Code",
    [string]$SessionId
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class User32Resume {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);
    public const int SW_RESTORE = 9;
}
"@

$toolsDir = $PSScriptRoot
$rootDir = Split-Path $toolsDir -Parent
$lockFile = Join-Path $toolsDir ".reload-resume-lock"
$contextFile = Join-Path $toolsDir ".reload-context.txt"
$resumeCmdFile = Join-Path $toolsDir ".kimi-resume-cmd.txt"

Write-Host "=== Kimi Safety-Net Resume ==="

# ── Wait for extension auto-resume to take precedence ─────────────
Write-Host "Waiting 12s for extension auto-resume..."
Start-Sleep -Seconds 12

# ── Check if extension already resumed ────────────────────────────
$kimiRunning = Get-Process -Name "kimi" -ErrorAction SilentlyContinue
if ($kimiRunning) {
    Write-Host "✅ Kimi process already running (PID $($kimiRunning.Id)). Extension auto-resume succeeded. Skipping safety-net." -ForegroundColor Green
    exit 0
}

# Check extension lock file
if (Test-Path $lockFile) {
    $lockAge = [math]::Round(((Get-Date) - (Get-Item $lockFile).LastWriteTime).TotalSeconds)
    if ($lockAge -lt 45) {
        Write-Host "✅ Extension lock file exists (age=${lockAge}s). Auto-resume in progress. Skipping safety-net." -ForegroundColor Green
        exit 0
    }
}

# ── Resolve session ID ────────────────────────────────────────────
if (-not $SessionId) {
    if (Test-Path $resumeCmdFile) {
        $cmdLine = Get-Content $resumeCmdFile -Raw
        $match = [regex]::Match($cmdLine, 'kimi\s+-r\s+(\S+)')
        if ($match.Success) {
            $SessionId = $match.Groups[1].Value
            Write-Host "Using session from .kimi-resume-cmd.txt: $SessionId"
        }
    }
}

if (-not $SessionId) {
    $sessionsDir = Join-Path $env:USERPROFILE ".kimi\sessions"
    if (Test-Path $sessionsDir) {
        $latest = Get-ChildItem -Path $sessionsDir -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latest) {
            $SessionId = $latest.Name
            Write-Host "Using most recent Kimi session: $SessionId"
        }
    }
    $savedSessionFile = Join-Path $toolsDir ".kimi-last-session"
    if ((-not $SessionId) -and (Test-Path $savedSessionFile)) {
        $SessionId = Get-Content $savedSessionFile -Raw
        Write-Host "Using saved Kimi session: $SessionId"
    }
}

if (-not $SessionId) {
    Write-Error "No Kimi session found."
    exit 1
}

# ── Resolve workspace ─────────────────────────────────────────────
$workDir = $rootDir
if (Test-Path $resumeCmdFile) {
    $cmdLine = Get-Content $resumeCmdFile -Raw
    $wmatch = [regex]::Match($cmdLine, '-w\s+"([^"]+)"')
    if ($wmatch.Success) {
        $workDir = $wmatch.Groups[1].Value
    }
}
Write-Host "Workspace: $workDir"

# ── Find VS Code: ─────────────────────────────────────────────────
$proc = Get-Process -Name "Code" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$WindowTitleSubstring*"
} | Select-Object -First 1

if (-not $proc) {
    $proc = Get-Process -Name "Code" -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowHandle -ne 0
    } | Select-Object -First 1
}

if (-not $proc) {
    Write-Error "VS Code: is not running."
    exit 1
}

Write-Host "Found VS Code: window: $($proc.MainWindowTitle)"

# ── Focus and send keys ────────────────────────────────────────────
if ([User32Resume]::IsIconic($proc.MainWindowHandle)) {
    [void][User32Resume]::ShowWindowAsync($proc.MainWindowHandle, [User32Resume]::SW_RESTORE)
    Start-Sleep -Milliseconds 300
}

[void][User32Resume]::SetForegroundWindow($proc.MainWindowHandle)
Start-Sleep -Milliseconds 1000

# Open/focus integrated terminal
[System.Windows.Forms.SendKeys]::SendWait("^`")
Start-Sleep -Milliseconds 800

# Send resume command with workspace
$safeWorkDir = $workDir -replace '\\', '\\'
$resumeCmd = "kimi -r $SessionId -w `"$safeWorkDir`""
[System.Windows.Forms.SendKeys]::SendWait($resumeCmd)
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Write-Host "Sent: $resumeCmd"

# ── Send context after TUI loads ──────────────────────────────────
Start-Sleep -Seconds 12
if (Test-Path $contextFile) {
    $ctx = Get-Content $contextFile -Raw
    if ($ctx.Length -gt 4000) { $ctx = $ctx.Substring(0, 4000) + "`n[truncated]" }
    [System.Windows.Forms.SendKeys]::SendWait($ctx)
    Start-Sleep -Milliseconds 400
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Write-Host "Context sent ($($ctx.Length) chars)."
} else {
    # If context was already consumed by extension, send a default
    [System.Windows.Forms.SendKeys]::SendWait("Continue from where we left off.")
    Start-Sleep -Milliseconds 400
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Write-Host "Default context sent."
}

Write-Host "Safety-net resume complete." -ForegroundColor Green
