# start-swarm-backend.ps1
# Starts the OrbitScribe swarm backend detached from the terminal.
# Uses pythonw on Windows to avoid a console window.
# Includes port-conflict auto-recovery: kills stale python backends or scans for free port.

param(
    [string]$BackendDir = (Join-Path (Join-Path $PSScriptRoot "..") "swarm-backend"),
    [int]$Port = 58081,
    [switch]$UsePython,
    [int]$PortScanRange = 10
)

function Test-PortInUse {
    param([int]$TestPort)
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $TestPort)
    try {
        $listener.Start()
        $listener.Stop()
        return $false
    } catch {
        return $true
    }
}

function Get-StalePythonPid {
    param([int]$TestPort)
    try {
        $lines = netstat -ano | findstr ":$TestPort"
        foreach ($line in $lines) {
            $parts = $line.Trim() -split '\s+'
            $pid = $parts[-1]
            if ($pid -match '^\d+$') {
                $task = tasklist /FI "PID eq $pid" /FO CSV /NH 2>$null
                if ($task -and $task.ToLower().Contains('python')) {
                    return [int]$pid
                }
            }
        }
    } catch {}
    return $null
}

function Find-FreePort {
    param([int]$StartPort, [int]$Range)
    for ($p = $StartPort; $p -lt $StartPort + $Range; $p++) {
        if (-not (Test-PortInUse -TestPort $p)) {
            return $p
        }
    }
    return $null
}

# Resolve port conflicts
if (Test-PortInUse -TestPort $Port) {
    $stalePid = Get-StalePythonPid -TestPort $Port
    if ($stalePid) {
        Write-Host "[PortGuard] Killing stale python.exe on port $Port (PID $stalePid)"
        taskkill /F /PID $stalePid 2>$null
        Start-Sleep -Seconds 1
        if (-not (Test-PortInUse -TestPort $Port)) {
            Write-Host "[PortGuard] Port $Port freed."
        } else {
            $freePort = Find-FreePort -StartPort ($Port + 1) -Range $PortScanRange
            if ($freePort) {
                Write-Host "[PortGuard] Port $Port still occupied. Using fallback port $freePort."
                $Port = $freePort
            } else {
                Write-Error "No free port found in range $($Port + 1)-$($Port + $PortScanRange - 1)"
                exit 1
            }
        }
    } else {
        $freePort = Find-FreePort -StartPort ($Port + 1) -Range $PortScanRange
        if ($freePort) {
            Write-Host "[PortGuard] Port $Port in use by foreign process. Using fallback port $freePort."
            $Port = $freePort
        } else {
            Write-Error "No free port found in range $($Port + 1)-$($Port + $PortScanRange - 1)"
            exit 1
        }
    }
}

# Check if already running on the resolved port
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
$env:SWARM_PORT = $Port
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
