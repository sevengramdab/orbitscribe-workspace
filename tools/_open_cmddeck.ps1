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

$proc = Get-Process -Name "Code" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*Visual Studio Code*"
} | Select-Object -First 1

if ($proc) {
    Write-Host "Found VS Code: window"
    if ([User32]::IsIconic($proc.MainWindowHandle)) {
        [void][User32]::ShowWindowAsync($proc.MainWindowHandle, [User32]::SW_RESTORE)
        Start-Sleep -Milliseconds 300
    }
    [void][User32]::SetForegroundWindow($proc.MainWindowHandle)
    Start-Sleep -Milliseconds 1000

    # Open Command Palette
    [System.Windows.Forms.SendKeys]::SendWait("^+p")
    Start-Sleep -Milliseconds 800

    # Type command
    [System.Windows.Forms.SendKeys]::SendWait("Open ORBIT Command Deck")
    Start-Sleep -Milliseconds 600

    # Press Enter
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Write-Host "Command sent"
} else {
    Write-Error "VS Code: not found"
}
