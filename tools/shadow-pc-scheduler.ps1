# Run this on Shadow PC as Administrator to auto-start on boot
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"`$env:USERPROFILE\simplepod-shadow\shadow-pc-start.bat`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName "SimplePodShadowNode" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force
Write-Host "Task registered. Shadow node will auto-start at logon."
