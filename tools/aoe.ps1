#!/usr/bin/env pwsh
<#
.SYNOPSIS
    AOE Unified Launcher — Fully Automatic. Zero manual compilation required.

.DESCRIPTION
    On first run, this script attempts to auto-compile the Rust binary.
    If Rust is installed and compilation succeeds, it uses the native binary.
    If Rust is missing, the linker is broken, or compilation fails for any
    reason, it silently falls back to the Python shim.

    You never need to run `cargo build` manually. Just use this script.

.USAGE
    .\tools\aoe.ps1 start
    .\tools\aoe.ps1 stop
    .\tools\aoe.ps1 status
    .\tools\aoe.ps1 failsafe
    .\tools\aoe.ps1 logs
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("start", "stop", "status", "failsafe", "logs", "build", "auto")]
    [string]$Command,

    [int]$Port = 58082,
    [int]$MemoryLimit = 256,
    [string]$Script = "swarm-backend/modes/aquaculture_mesh_mode.py"
)

$RustExe = Join-Path $PSScriptRoot "..\aoe\supervisor\target\release\aoe.exe"
$PythonShim = Join-Path $PSScriptRoot "aoe_supervisor.py"

function Get-SupervisorPid {
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 -and $_.State -eq "Listen" }
        $conn = $conns | Select-Object -First 1
        if ($conn) {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            if ($proc) { return $proc.Id }
        }
    } catch {}
    return $null
}

function Test-RustAvailable {
    # Try PATH first
    $cargo = Get-Command cargo -ErrorAction SilentlyContinue
    if ($cargo) {
        try {
            $ver = & cargo --version 2>$null
            return ($ver -match "cargo")
        } catch { return $false }
    }
    # Fallback to known rustup location
    $cargoPath = Join-Path $env:USERPROFILE ".cargo\bin\cargo.exe"
    if (Test-Path $cargoPath) {
        try {
            $ver = & $cargoPath --version 2>$null
            return ($ver -match "cargo")
        } catch { return $false }
    }
    return $false
}

function Invoke-AutoBuild {
    if (Test-Path $RustExe) { return $true }

    if (-not (Test-RustAvailable)) {
        Write-Host "[AOE] Rust toolchain not found. Skipping auto-build."
        return $false
    }

    # Determine cargo path
    $cargoCmd = "cargo"
    $cargoPath = Join-Path $env:USERPROFILE ".cargo\bin\cargo.exe"
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue) -and (Test-Path $cargoPath)) {
        $cargoCmd = $cargoPath
    }

    Write-Host "[AOE] Rust detected. Auto-compiling aoe.exe (this may take a few minutes)..."
    $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
    $supervisorDir = Resolve-Path (Join-Path $PSScriptRoot "..\aoe\supervisor")

    Push-Location $supervisorDir
    try {
        & $cargoCmd build --release 2>&1 | ForEach-Object { Write-Host "[AOE-BUILD] $_" }
        $built = $LASTEXITCODE -eq 0
    } catch {
        Write-Host "[AOE] Auto-build failed: $_"
        $built = $false
    } finally {
        Pop-Location
    }

    if ($built -and (Test-Path $RustExe)) {
        Write-Host "[AOE] Auto-build succeeded. Native binary ready."
        return $true
    } else {
        Write-Host "[AOE] Auto-build failed. Falling back to Python shim."
        return $false
    }
}

function Start-Supervisor {
    $existing = Get-SupervisorPid
    if ($existing) {
        Write-Host "[AOE] Supervisor already running (PID $existing)"
        return $existing
    }

    # Attempt silent auto-build on first run
    $useRust = Invoke-AutoBuild

    $projRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
    $pythonPath = "$projRoot\swarm-backend"

    if ($useRust -and (Test-Path $RustExe)) {
        Write-Host "[AOE] Launching native Rust supervisor (aoe.exe)"
        $proc = Start-Process -FilePath $RustExe -ArgumentList "--port", $Port, "--memory-limit", $MemoryLimit -PassThru -WindowStyle Hidden
    } else {
        Write-Host "[AOE] Launching Python supervisor shim"
        $env:PYTHONPATH = $pythonPath
        $quotedShim = '"{0}"' -f $PythonShim
        $quotedScript = '"{0}"' -f "$projRoot\$Script"
        $proc = Start-Process -FilePath "python" -ArgumentList $quotedShim, "--port", $Port, "--script", $quotedScript, "--memory-limit", $MemoryLimit -PassThru -NoNewWindow
    }

    Start-Sleep -Seconds 3
    $pidNow = Get-SupervisorPid
    if ($pidNow) {
        Write-Host "[AOE] Supervisor online (PID $pidNow)"
    } else {
        Write-Host "[AOE] WARNING: Supervisor did not bind to port $Port within 3 seconds"
    }
    return $pidNow
}

function Stop-Supervisor {
    $pidNow = Get-SupervisorPid
    if ($pidNow) {
        Stop-Process -Id $pidNow -Force
        Write-Host "[AOE] Supervisor stopped."
    } else {
        Write-Host "[AOE] No supervisor running on port $Port"
    }
}

function Invoke-AoeCli {
    param([string]$SubCommand)
    & python (Join-Path $PSScriptRoot "aoe_mesh.py") $SubCommand
}

switch ($Command) {
    "start" {
        Start-Supervisor | Out-Null
        Invoke-AoeCli "start"
    }
    "stop" {
        Invoke-AoeCli "stop"
        Stop-Supervisor
    }
    "status" {
        Invoke-AoeCli "status"
    }
    "failsafe" {
        Invoke-AoeCli "failsafe"
        Stop-Supervisor
    }
    "logs" {
        Invoke-AoeCli "logs"
    }
    "auto" {
        # Dispatch intent via backend auto mode
        $body = @{ message = $Script; mode = "auto"; session_id = "aoe-cli-$(Get-Random)" } | ConvertTo-Json
        $url = "http://localhost:58081/api/chat"
        try {
            $resp = Invoke-RestMethod -Uri $url -Method POST -ContentType "application/json" -Body $body -TimeoutSec 60
            if ($resp -match '"error"' -or $resp -match '"Unknown mode"') {
                throw "Backend returned error"
            }
            Write-Host "[AOE] Intent dispatched. Response:"
            Write-Host ($resp | ConvertTo-Json -Depth 3)
        } catch {
            Write-Host "[AOE] Backend not available or outdated. Falling back to local intent router..."
            $env:PYTHONPATH = "$env:PYTHONPATH;$(Resolve-Path .)\swarm-backend"
            $result = python -c "
import json
import sys
sys.path.insert(0, 'swarm-backend')
from core.intent_router import classify_intent
r = classify_intent('$Script')
print(json.dumps({
    'intent': r.intent.value,
    'confidence': r.confidence,
    'mode': r.target_mode,
    'roles': r.target_roles,
    'reasoning': r.reasoning
}))
" 2>&1
            Write-Host $result
        }
    }
    "build" {
        # Force a rebuild even if binary exists
        if (Test-Path $RustExe) {
            Remove-Item $RustExe -Force
            Write-Host "[AOE] Existing binary cleared. Rebuilding..."
        }
        $result = Invoke-AutoBuild
        if ($result) {
            Write-Host "[AOE] Build complete: $RustExe"
        } else {
            Write-Host "[AOE] Build failed. Check output above for linker or dependency errors."
        }
    }
}
