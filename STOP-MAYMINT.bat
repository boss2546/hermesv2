@echo off
title Stop Maymint Services - Hermes v2
cd /d "%~dp0"
echo =======================================================================
echo    🛑 Stopping all Maymint & LiveKit Services
echo =======================================================================
echo.
powershell -Command "
Get-Process -Name 'livekit-server' -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name 'powershell' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*Maymint*' } | Stop-Process -Force
$netstat = netstat -ano | Select-String ':9229|:7880'
foreach ($line in $netstat) {
    $m = [regex]::Match($line, '\s+(\d+)$')
    if ($m.Success) {
        Stop-Process -Id $m.Groups[1].Value -Force -ErrorAction SilentlyContinue
    }
}
Write-Host '✅ All Maymint and LiveKit processes stopped cleanly.' -ForegroundColor Green
"
pause
