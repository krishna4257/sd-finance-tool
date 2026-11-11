# WSL Watchdog Script for SD-FIN-SERVER
# Checks if the Ubuntu WSL2 instance is running every 30 minutes; restarts it if stopped.

$logDir = "C:\ProgramData\sd-finance"
$logFile = "$logDir\wsl-watchdog.log"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

try {
    $wslList = (wsl.exe -l -v | Out-String) -replace "`0", ""
    if ($wslList -notmatch "Ubuntu\s+Running") {
        $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        Add-Content -Path $logFile -Value "[$timestamp] WARNING: Ubuntu WSL is NOT running. Initiating restart..."
        
        # Start Ubuntu in background
        Start-Process -FilePath "C:\Windows\System32\wsl.exe" -ArgumentList "-d Ubuntu -e /bin/true" -WindowStyle Hidden
        Start-Sleep -Seconds 10
        
        $checkList = (wsl.exe -l -v | Out-String) -replace "`0", ""
        if ($checkList -match "Ubuntu\s+Running") {
            Add-Content -Path $logFile -Value "[$timestamp] SUCCESS: Ubuntu WSL restarted successfully."
        } else {
            Add-Content -Path $logFile -Value "[$timestamp] ERROR: Ubuntu WSL failed to restart."
        }
    }
} catch {
    $err = $_.Exception.Message
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $logFile -Value "[$timestamp] ERROR in watchdog script: $err"
}
