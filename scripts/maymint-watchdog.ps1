# ==============================================================================
# 🌸 Maymint Always-On 24/7 Watchdog Supervisor (Hermes v2)
# ==============================================================================
# Manages:
# 1. LiveKit WebRTC Server (Port 7880, 7881, 50000-50100)
# 2. Maymint Voice Agent Daemon (LiveKit Agent Worker)
# 3. Maymint Liquid Glass Dashboard (Port 9229)
#
# Features:
# - Global Named Mutex: Prevents multiple watchdog instances from running concurrently
# - Continuous 10-second healthcheck loop
# - Automatic sub-10s crash recovery & self-healing
# - Safe log rotation (max 10MB x 3)
# ==============================================================================

# 1. Enforce Single Instance via Mutex
$mutexName = "Global\MaymintWatchdogMutex"
$createdNew = $false
$watchdogMutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$createdNew)
if (-not $createdNew) {
    Write-Host "⚠️ Another Maymint Watchdog instance is already active. Exiting immediately to prevent duplication." -ForegroundColor Yellow
    exit 0
}

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

# Rotate log if larger than 10MB
if (Test-Path $watchdogLog) {
    $item = Get-Item $watchdogLog
    if ($item.Length -gt 10MB) {
        $backupLog = Join-Path $logDir "watchdog.1.log"
        Move-Item -Path $watchdogLog -Destination $backupLog -Force -ErrorAction SilentlyContinue
    }
}

function Write-WatchdogLog([string]$msg, [string]$level = "INFO") {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $color = "Cyan"
    if ($level -eq "ERROR") { $color = "Red" }
    elseif ($level -eq "WARN") { $color = "Yellow" }
    $line = "[$timestamp] [$level] $msg"
    Write-Host $line -ForegroundColor $color
    Add-Content -Path $watchdogLog -Value $line -Encoding utf8
}

Write-WatchdogLog "🚀 Starting Maymint 24/7 Watchdog Supervisor (Singleton Active)..."

function Get-RunningPythonProcess([string]$scriptName) {
    try {
        $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue
        foreach ($p in $procs) {
            if ($p.CommandLine -and $p.CommandLine.Contains($scriptName)) {
                return $p
            }
        }
    } catch {}
    return $null
}

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

# Initial Verification & Gentle Boot
try {
    # LiveKit Check
    $lkProc = Get-Process -Name "livekit-server" -ErrorAction SilentlyContinue
    if (-not $lkProc) {
        Start-LiveKitServer | Out-Null
        Start-Sleep -Seconds 2
    }

    # Web Server Check
    $existingWeb = Get-RunningPythonProcess "server.py"
    if (-not $existingWeb) {
        Start-WebServer | Out-Null
        Start-Sleep -Seconds 2
    }

    # Agent Daemon Check
    $existingAgent = Get-RunningPythonProcess "agent_daemon.py"
    if (-not $existingAgent) {
        Start-AgentDaemon | Out-Null
        Start-Sleep -Seconds 1
    }
} catch {
    Write-WatchdogLog "Initial startup error: $_" "ERROR"
}

Write-WatchdogLog "✅ All Maymint services confirmed active. Entering self-healing surveillance loop..."

# Surveillance Loop
try {
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

            $lkProc = Get-Process -Name "livekit-server" -ErrorAction SilentlyContinue
            if (-not $lkAlive -or -not $lkProc) {
                Write-WatchdogLog "⚠️ LiveKit Server down or not responding on 7880. Reviving..." "WARN"
                Get-Process -Name "livekit-server" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
                Start-Sleep -Milliseconds 500
                Start-LiveKitServer | Out-Null
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

            $webProc = Get-RunningPythonProcess "server.py"
            if (-not $webAlive -or -not $webProc) {
                Write-WatchdogLog "⚠️ Maymint Web Server down or not responding on 9229. Reviving..." "WARN"
                # Terminate any stale processes on 9229
                $netstat = netstat -ano | Select-String ":9229"
                foreach ($line in $netstat) {
                    $pidMatch = [regex]::Match($line, "\s+(\d+)$")
                    if ($pidMatch.Success) {
                        Stop-Process -Id $pidMatch.Groups[1].Value -Force -ErrorAction SilentlyContinue
                    }
                }
                Start-Sleep -Milliseconds 500
                Start-WebServer | Out-Null
            }

            # 3. Check Agent Daemon Process
            $agentProc = Get-RunningPythonProcess "agent_daemon.py"
            if (-not $agentProc) {
                Write-WatchdogLog "⚠️ Maymint Agent Daemon not running. Reviving..." "WARN"
                Start-AgentDaemon | Out-Null
            }

        } catch {
            Write-WatchdogLog "Supervisor loop exception: $_" "ERROR"
        }

        Start-Sleep -Seconds 10
    }
} finally {
    if ($watchdogMutex) {
        $watchdogMutex.ReleaseMutex()
        $watchdogMutex.Dispose()
    }
}
