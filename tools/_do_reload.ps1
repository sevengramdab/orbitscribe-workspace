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

$proc = Get-Process -Name "Code" | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*Visual Studio Code*" } | Select-Object -First 1
if ($proc) {
    if ([User32]::IsIconic($proc.MainWindowHandle)) { [User32]::ShowWindowAsync($proc.MainWindowHandle, [User32]::SW_RESTORE); Start-Sleep -Milliseconds 300 }
    [User32]::SetForegroundWindow($proc.MainWindowHandle)
    Start-Sleep -Milliseconds 800
    [System.Windows.Forms.SendKeys]::SendWait("^+p")
    Start-Sleep -Milliseconds 600
    [System.Windows.Forms.SendKeys]::SendWait("Developer: Reload Window")
    Start-Sleep -Milliseconds 400
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Write-Host "Reload sent successfully."
} else {
    Write-Error "VS Code: not found."
}
