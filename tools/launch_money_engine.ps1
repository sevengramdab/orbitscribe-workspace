# launch_money_engine.ps1
# =======================
# Starts the OrbitScribe backend and then launches the Money Engine swarm.
#
# Usage:
#   .\tools\launch_money_engine.ps1 -Autopilot
#   .\tools\launch_money_engine.ps1 -Verticals content,affiliate,saas

param(
    [switch]$Autopilot,
    [string]$Verticals = "",
    [int]$Interval = 300,
    [switch]$OneShot
)

$ErrorActionPreference = "Stop"

function Test-Backend {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:58081/api/health" -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MONEY ENGINE LAUNCHER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Ensure backend is running
if (-not (Test-Backend)) {
    Write-Host "[INFO] Backend not running. Starting..." -ForegroundColor Yellow
    $backendPath = Join-Path $PSScriptRoot "..\swarm-backend\main.py"
    Start-Process python -ArgumentList "$backendPath" -WindowStyle Hidden
    $tries = 0
    while (-not (Test-Backend) -and $tries -lt 20) {
        Start-Sleep -Seconds 1
        $tries++
    }
    if (-not (Test-Backend)) {
        Write-Host "[ERROR] Backend failed to start." -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Backend is up." -ForegroundColor Green
} else {
    Write-Host "[OK] Backend already running." -ForegroundColor Green
}

# 2. Build payload
$payload = @{
    autonomy_tier = if ($Autopilot) { "AUTOPILOT" } else { "DEFAULT" }
    interval_seconds = $Interval
    one_shot = [bool]$OneShot
}
if ($Verticals) {
    $payload.verticals = $Verticals -split ","
}

# 3. Start the money engine
Write-Host "[INFO] Starting Money Engine..." -ForegroundColor Cyan
$body = $payload | ConvertTo-Json -Depth 3
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:58081/api/money-engine/start" -Method POST -Body $body -ContentType "application/json"
Write-Host "[OK] Money Engine started." -ForegroundColor Green
Write-Host ($resp | ConvertTo-Json -Depth 3)

# 4. Show status
Start-Sleep -Seconds 2
$status = Invoke-RestMethod -Uri "http://127.0.0.1:58081/api/money-engine/status"
Write-Host "`nCurrent Status:" -ForegroundColor Cyan
Write-Host "Revenue: `$$(($status.total_revenue).ToString('F2'))" -ForegroundColor Green
Write-Host "Costs:   `$$(($status.total_costs).ToString('F2'))" -ForegroundColor Red
Write-Host "Profit:  `$$(($status.net_profit).ToString('F2'))" -ForegroundColor $(if ($status.net_profit -ge 0) { "Green" } else { "Red" })
Write-Host "Agents:  $(($status.agents | Measure-Object).Count) running" -ForegroundColor White
