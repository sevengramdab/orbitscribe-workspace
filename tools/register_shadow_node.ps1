# Register Shadow Node as auto-start Windows Scheduled Task
$TaskName = "SimplePodShadowNode"
$ShadowDir = "$env:USERPROFILE\simplepod-shadow"
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$ShadowDir\shadow-pc-start.bat`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Stop existing task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force
Write-Host "Shadow node registered for auto-start at logon."

# Start it now only if not already listening on 8002
$listener = Get-NetTCPConnection -LocalPort 8002 -ErrorAction SilentlyContinue
if (-not $listener) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Shadow node started."
} else {
    Write-Host "Shadow node already running on port 8002 - skipped duplicate start."
}
