# start-swarm-backend.ps1
# Starts the OrbitScribe swarm backend detached from the terminal.
# Uses pythonw on Windows to avoid a console window.

param(
    [string]$BackendDir = (Join-Path (Join-Path $PSScriptRoot "..") "swarm-backend"),
    [int]$Port = 58081,
    [switch]$UsePython
)

# Check if already running
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -Method GET -TimeoutSec 2
    Write-Host "Swarm backend already running on port $Port (status: $($resp.status))"
    exit 0
} catch {
    # Not running, proceed to start
}

$mainPy = Join-Path $BackendDir "main.py"
if (-not (Test-Path $mainPy)) {
    Write-Error "main.py not found at: $mainPy"
    exit 1
}

# Prefer pythonw on Windows (no console window), fallback to python
$python = if ($UsePython) { "python" } else { "pythonw" }
try {
    $null = & $python --version 2>&1
} catch {
    $python = "python"
    $null = & $python --version 2>&1
}

Write-Host "Starting swarm backend: $python $mainPy (port $Port)"

# Start detached using Start-Process
$proc = Start-Process -FilePath $python -ArgumentList $mainPy -WorkingDirectory $BackendDir `
    -WindowStyle Hidden -PassThru

# Wait for health
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -Method GET -TimeoutSec 2
        Write-Host "Swarm backend online (status: $($resp.status), api_mode: $($resp.api_mode))"
        exit 0
    } catch {
        # keep polling
    }
}

Write-Error "Swarm backend failed to start within 15 seconds"
exit 1
