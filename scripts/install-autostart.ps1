# ==============================================================================
# 🌸 Register Maymint 24/7 Always-On in Windows Task Scheduler
# ==============================================================================

$taskName = "Maymint-AlwaysOn"
$baseDir = Split-Path -Parent $PSScriptRoot
$watchdogScript = Join-Path $baseDir "scripts\maymint-watchdog.ps1"

Write-Host "Registering Scheduled Task '$taskName'..." -ForegroundColor Cyan

# Action: launch powershell hidden running watchdog
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$watchdogScript`"" -WorkingDirectory $baseDir

# Trigger: At startup
$trigger = New-ScheduledTaskTrigger -AtStartup

# Settings: Restart if fails, run indefinitely
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 365)

# Register with SYSTEM or current user with highest privileges
try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -User "$env:USERDOMAIN\$env:USERNAME" -RunLevel Highest | Out-Null
    Write-Host "✅ Task '$taskName' registered successfully! It will start automatically at Windows boot." -ForegroundColor Green
} catch {
    Write-Host "⚠️ Warning registering task: $_" -ForegroundColor Yellow
}
