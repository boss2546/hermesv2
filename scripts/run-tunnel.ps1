# ==============================================================================
# 🌐 Cloudflare Quick Tunnel for Hermes v2 (Port 9229 - Voice Web Dashboard)
# ==============================================================================

param(
    [int]$Port = 9229
)

$baseDir = Split-Path -Parent $PSScriptRoot
$urlFileRoot = Join-Path $baseDir "TUNNEL_URL.txt"
$logDir = Join-Path $baseDir "logs"
$logFile = Join-Path $logDir "tunnel.log"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Remove-Item $logFile -Force -ErrorAction SilentlyContinue

Write-Host "🌐 กำลังเชื่อมต่อ Cloudflare Quick Tunnel (Port $Port)..." -ForegroundColor Yellow

$proc = Start-Process -FilePath "C:\Windows\System32\cloudflared.exe" `
    -ArgumentList "tunnel --url http://127.0.0.1:$Port --logfile `"$logFile`"" `
    -PassThru

# Extract Public URL from log
$url = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $logFile) {
        $content = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
        if ($content -match "https://([a-zA-Z0-9-]+)\.trycloudflare\.com") {
            $url = $matches[0]
            break
        }
    }
}

if ($url) {
    $info = @"
===============================================================================
  🌸 Hermes v2 — Cloudflare Public Tunnel (HTTPS Free 100%)
===============================================================================
  สถานะ: เชื่อมต่อสำเร็จ พร้อมใช้งานจากทุกที่ทั่วโลก!

  🔗 Public URL:
     $url

  🎙️ Maymint Voice Dashboard (Liquid Glass Web UI):
     $url/

  ⚙️ Configuration API:
     $url/api/config

  🌐 Local Direct Access:
     http://127.0.0.1:$Port/
===============================================================================
"@
    Set-Content -Path $urlFileRoot -Value $info -Encoding UTF8
    Write-Host "`n✅ เชื่อมต่อ Cloudflare Tunnel สำเร็จสมบูรณ์!" -ForegroundColor Green
    Write-Host "🔗 Public HTTPS URL: $url" -ForegroundColor Cyan
    Write-Host "📄 บันทึกลิงก์ไว้ที่: $urlFileRoot`n" -ForegroundColor Gray
} else {
    Write-Host "⚠️ ไม่สามารถดึง URL จาก Cloudflare Tunnel ได้ กรุณาตรวจสอบ logs/tunnel.log" -ForegroundColor Red
}

Write-Host "💡 Tunnel กำลังทำงาน... กด Ctrl+C เพื่อหยุดการทำงาน`n" -ForegroundColor DarkGray
$proc.WaitForExit()
