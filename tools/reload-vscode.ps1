# reload-vscode.ps1
# Reloads VS Code: and auto-resumes Kimi via a fully detached safety-net process.
# NOTE: Full window reload breaks Kimi Code: webview state (Kimi extension limitation).
# By default this now uses Extension Host restart which preserves all webviews.
# Use -FullReload only when you truly need a full window reload.

param(
    [string]$WindowTitleSubstring = "Visual Studio Code",
    [int]$PreDelayMs = 800,
    [int]$AfterPaletteMs = 600,
    [int]$AfterTypeMs = 400,
    [switch]$FullReload,
    [switch]$ForceResume,
    [switch]$KillKimiFirst
)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class User32 {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);
    public const int SW_RESTORE = 9;
}
"@

Add-Type -AssemblyName System.Windows.Forms

# -- Loop protection ------------------------------------------------
$lockFile = Join-Path $PSScriptRoot ".reload-lock"
$lockCooldownSeconds = 15

if (Test-Path $lockFile) {
    $lastReload = Get-Content $lockFile -Raw -ErrorAction SilentlyContinue
    if ($lastReload) {
        try {
            $lastTime = [datetime]::Parse($lastReload)
            $elapsed = ([datetime]::UtcNow - $lastTime).TotalSeconds
            if ($elapsed -lt $lockCooldownSeconds) {
                Write-Host "Reload blocked: already reloaded ${elapsed:N1}s ago." -ForegroundColor Yellow
                exit 0
            }
        } catch {}
    }
}
[datetime]::UtcNow.ToString("o") | Set-Content -Path $lockFile -Force

# -- Find VS Code: window -------------------------------------------
$codeProcess = Get-Process -Name "Code" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$WindowTitleSubstring*"
} | Select-Object -First 1
if (-not $codeProcess) {
    $codeProcess = Get-Process -Name "Code" -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowHandle -ne 0
    } | Select-Object -First 1
}
if (-not $codeProcess) {
    Write-Error "VS Code: not found."
    exit 1
}

# -- DEFAULT: Extension Host restart (preserves Kimi webview) -------
# Full window reload destroys Kimi Code: webview state. Kimi does NOT
# auto-restore the active conversation after a window reload - this is
# a limitation of the Kimi extension itself.
$reloadCommand = if ($FullReload) { "Developer: Reload Window" } else { "Developer: Restart Extension Host" }

if ($FullReload) {
    Write-Warning "FULL RELOAD selected. This will break Kimi Code: webview state. You will need to manually reopen your chat from History."
}

# -- Send reload keys -----------------------------------------------
if ([User32]::IsIconic($codeProcess.MainWindowHandle)) {
    [void][User32]::ShowWindowAsync($codeProcess.MainWindowHandle, [User32]::SW_RESTORE)
    Start-Sleep -Milliseconds 300
}
[void][User32]::SetForegroundWindow($codeProcess.MainWindowHandle)
Start-Sleep -Milliseconds $PreDelayMs

[System.Windows.Forms.SendKeys]::SendWait("^+p")
Start-Sleep -Milliseconds $AfterPaletteMs
[System.Windows.Forms.SendKeys]::SendWait($reloadCommand)
Start-Sleep -Milliseconds $AfterTypeMs
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")

Write-Host "$reloadCommand sent." -ForegroundColor Green

# -- Auto-resume Kimi after reload ----------------------------------
# Even Extension Host restart can disrupt Kimi Code: webview state.
# Spawn a detached safety-net process that waits then resumes Kimi.
$resumeScript = Join-Path $PSScriptRoot "resume-kimi.ps1"
if (Test-Path $resumeScript) {
    Write-Host "Safety-net: scheduling Kimi resume in 6s..." -ForegroundColor DarkGray
    Start-Process powershell.exe -ArgumentList @(
        "-ExecutionPolicy", "Bypass",
        "-File", "$resumeScript"
    ) -WindowStyle Hidden
} else {
    Write-Warning "resume-kimi.ps1 not found. Kimi may need manual resume after reload."
}

if (-not $FullReload) {
    Write-Host "Kimi webview should be preserved. OrbitScribe extension will reload." -ForegroundColor Cyan
}
