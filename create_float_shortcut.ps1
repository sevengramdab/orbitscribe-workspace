$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\Shadow\Desktop\Voice to Text Float.lnk")
$Shortcut.TargetPath = "C:\Windows\System32\cmd.exe"
$Shortcut.Arguments = '/k ""C:\Users\Shadow\voice to text engine\start_float.bat""'
$Shortcut.WorkingDirectory = "C:\Users\Shadow\voice to text engine"
$Shortcut.IconLocation = "C:\Users\Shadow\voice to text engine\voice_to_text.ico,0"
$Shortcut.Description = "Voice to Text - Floating Window"
$Shortcut.Save()
Write-Host "Shortcut created successfully at C:\Users\Shadow\Desktop\Voice to Text Float.lnk"
