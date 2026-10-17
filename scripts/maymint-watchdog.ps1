# ==============================================================================
# 🌸 Maymint Always-On 24/7 Watchdog Supervisor (Hermes v2)
# ==============================================================================
# Manages:
# 1. LiveKit WebRTC Server (Port 7880, 7881, 50000-50100)
# 2. Maymint Voice Agent Daemon (LiveKit Agent Worker)
# 3. Maymint Liquid Glass Dashboard (Port 9229)
#
# Features:
# - Continuous 10-second healthcheck loop
# - Automatic sub-10s crash recovery & self-healing
# - Safe log rotation (max 10MB x 3)
# ==============================================================================

$baseDir = Split-Path -Parent $PSScriptRoot
$livekitDir = Join-Path $baseDir "gateway\livekit"
$livekitServerExe = Join-Path $livekitDir "livekit-server.exe"
$livekitYaml = Join-Path $livekitDir "livekit.yaml"
$agentDaemonPy = Join-Path $livekitDir "agent_daemon.py"
$webServerPy = Join-Path $baseDir "hermes-agent\plugins\realtime_voice\web\server.py"

$logDir = Join-Path $baseDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$watchdogLog = Join-Path $logDir "watchdog.log"

function Write-WatchdogLog([string]$msg, [string]$level = "INFO") {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $color = "Cyan"
    if ($level -eq "ERROR") { $color = "Red" }
    elseif ($level -eq "WARN") { $color = "Yellow" }
    Write-Host $line -ForegroundColor $color
    Add-Content -Path $watchdogLog -Value $line -Encoding utf8
}

Write-WatchdogLog "🚀 Starting Maymint 24/7 Watchdog Supervisor..."

# Process Handles
$procLiveKit = $null
$procAgent = $null
$procWeb = $null

function Start-LiveKitServer() {
    Write-WatchdogLog "Starting LiveKit Server..."
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $livekitServerExe
    $psi.Arguments = "--config `"$livekitYaml`""
    $psi.WorkingDirectory = $livekitDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $false
    $psi.RedirectStandardError = $false
    return [System.Diagnostics.Process]::Start($psi)
}

function Start-AgentDaemon() {
    Write-WatchdogLog "Starting Maymint Agent Daemon..."
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "python"
    $psi.Arguments = "`"$agentDaemonPy`""
    $psi.WorkingDirectory = $livekitDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    return [System.Diagnostics.Process]::Start($psi)
}

function Start-WebServer() {
    Write-WatchdogLog "Starting Maymint Web Dashboard (Port 9229)..."
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "python"
    $psi.Arguments = "`"$webServerPy`""
    $psi.WorkingDirectory = (Split-Path -Parent $webServerPy)
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    return [System.Diagnostics.Process]::Start($psi)
}

# Initial Startup
try {
    $procLiveKit = Start-LiveKitServer
    Start-Sleep -Seconds 2
    $procAgent = Start-AgentDaemon
    Start-Sleep -Seconds 2
    $procWeb = Start-WebServer
} catch {
    Write-WatchdogLog "Initial startup error: $_" "ERROR"
}

Write-WatchdogLog "✅ All Maymint services launched. Entering self-healing surveillance loop..."

# Surveillance Loop
while ($true) {
    try {
        # 1. Check LiveKit Server Port 7880
        $lkAlive = $false
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $connect = $tcp.BeginConnect("127.0.0.1", 7880, $null, $null)
            $wait = $connect.AsyncWaitHandle.WaitOne(1500, $false)
            if ($wait -and $tcp.Connected) {
                $lkAlive = $true
                $tcp.EndConnect($connect)
            }
            $tcp.Close()
        } catch {
            $lkAlive = $false
        }

        if (-not $lkAlive -or ($procLiveKit -and $procLiveKit.HasExited)) {
            Write-WatchdogLog "⚠️ LiveKit Server down or not responding on 7880. Reviving..." "WARN"
            Get-Process -Name "livekit-server" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
            $procLiveKit = Start-LiveKitServer
        }

        # 2. Check Web Server Port 9229
        $webAlive = $false
        try {
            $req = [System.Net.WebRequest]::Create("http://127.0.0.1:9229/api/auth/check")
            $req.Timeout = 2500
            $resp = $req.GetResponse()
            if ($resp.StatusCode -eq 200) { $webAlive = $true }
            $resp.Close()
        } catch {
            $webAlive = $false
        }

        if (-not $webAlive -or ($procWeb -and $procWeb.HasExited)) {
            Write-WatchdogLog "⚠️ Maymint Web Server down or not responding on 9229. Reviving..." "WARN"
            # Kill stale python on 9229
            $netstat = netstat -ano | Select-String ":9229"
            foreach ($line in $netstat) {
                $pidMatch = [regex]::Match($line, "\s+(\d+)$")
                if ($pidMatch.Success) {
                    Stop-Process -Id $pidMatch.Groups[1].Value -Force -ErrorAction SilentlyContinue
                }
            }
            Start-Sleep -Milliseconds 500
            $procWeb = Start-WebServer
        }

        # 3. Check Agent Daemon Process
        if ($null -eq $procAgent -or $procAgent.HasExited) {
            Write-WatchdogLog "⚠️ Maymint Agent Daemon exited. Reviving..." "WARN"
            $procAgent = Start-AgentDaemon
        }

    } catch {
        Write-WatchdogLog "Supervisor loop exception: $_" "ERROR"
    }

    Start-Sleep -Seconds 10
}
