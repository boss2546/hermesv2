# ==============================================================================
# 🌐 Cloudflare Named Tunnel (Custom Domain / Cloudflare Token)
# ==============================================================================

param(
    [string]$TunnelToken = "",
    [int]$Port = 9229
)

$baseDir = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $baseDir ".env"

if (-not $TunnelToken -and (Test-Path $envFile)) {
    $tokenLine = Get-Content $envFile | Where-Object { $_ -match "^CLOUDFLARE_TUNNEL_TOKEN=(.+)" }
    if ($tokenLine) {
        $TunnelToken = ($tokenLine -split "=", 2)[1].Trim()
    }
}

if (-not $TunnelToken) {
    Write-Host "==================================================================" -ForegroundColor Yellow
    Write-Host "  🔑 กรุณาระบุ Cloudflare Tunnel Token เพื่อเชื่อมต่อ Domain ของคุณ" -ForegroundColor Yellow
    Write-Host "==================================================================" -ForegroundColor Yellow
    $TunnelToken = Read-Host "วาง Cloudflare Tunnel Token ที่นี่"
}

if (-not $TunnelToken) {
    Write-Host "❌ ยกเลิก: ไม่พบ Token" -ForegroundColor Red
    exit 1
}

# Save to .env if not exists
if (Test-Path $envFile) {
    $content = Get-Content $envFile -Raw
    if ($content -notmatch "CLOUDFLARE_TUNNEL_TOKEN=") {
        Add-Content -Path $envFile -Value "`nCLOUDFLARE_TUNNEL_TOKEN=$TunnelToken"
    }
}

Write-Host "`n🚀 กำลังเชื่อมต่อ Cloudflare Named Tunnel ด้วย Token..." -ForegroundColor Cyan
& "C:\Windows\System32\cloudflared.exe" tunnel run --token $TunnelToken
