# Map local PC share to Shadow as Z: drive
# Fill in the 4 values below, then run this script in PowerShell

$LocalPC_IP    = "192.168.1.xxx"   # <-- Your local PC's IP (find it via ipconfig on your local machine)
$ShareName     = "WD4TB"           # <-- The share name you created on your local PC
$Username      = "your_username"   # <-- Your local PC username
$Password      = "your_password"   # <-- Your local PC password (or leave blank to prompt)

# Optional: Remove old mapping if exists
net use Z: /delete 2>$null

# Map the drive
if ($Password -eq "your_password") {
    Write-Host "ERROR: You need to edit this file and fill in your real credentials!" -ForegroundColor Red
    exit 1
}

net use Z: "\\$LocalPC_IP\$ShareName" /user:$Username $Password /persistent:yes

if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: Z: drive mapped to \\$LocalPC_IP\$ShareName" -ForegroundColor Green
    Get-PSDrive Z | Select-Object Name, Root, Used, Free
} else {
    Write-Host "FAILED to map drive. Common fixes:" -ForegroundColor Red
    Write-Host "  1. Make sure your local PC has the folder shared (Right-click -> Properties -> Sharing)"
    Write-Host "  2. Check that your local PC's firewall allows SMB (port 445)"
    Write-Host "  3. If on different networks, use a VPN (Tailscale/ZeroTier) or cloud storage instead"
}
