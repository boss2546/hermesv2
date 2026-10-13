$ErrorActionPreference = "Continue"

$workspace = "c:\Users\Administrator\Desktop\hermes2"
$scratchDir = "$workspace\scratch"
if (-not (Test-Path $scratchDir)) {
    New-Item -ItemType Directory -Force -Path $scratchDir | Out-Null
}

$lkLog = "$scratchDir\livekit-tunnel.log"
$uiLog = "$scratchDir\playground-tunnel.log"

Remove-Item $lkLog -Force -ErrorAction SilentlyContinue
Remove-Item $uiLog -Force -ErrorAction SilentlyContinue

Write-Host "🌐 Step 1: Starting Cloudflare Tunnel for LiveKit Signaling (Port 7880)..." -ForegroundColor Yellow
$procLk = Start-Process -FilePath "C:\Windows\System32\cloudflared.exe" -ArgumentList "tunnel --url http://127.0.0.1:7880 --logfile `"$lkLog`"" -PassThru

# Wait for LiveKit URL
$lkUrl = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $lkLog) {
        $content = Get-Content $lkLog -Raw -ErrorAction SilentlyContinue
        if ($content -match "https://([a-zA-Z0-9-]+)\.trycloudflare\.com") {
            $lkUrl = $matches[0]
            break
        }
    }
}

if (-not $lkUrl) {
    Write-Host "❌ Failed to get LiveKit Tunnel URL." -ForegroundColor Red
    exit 1
}

$lkWsUrl = $lkUrl.Replace("https://", "wss://")
Write-Host "✅ LiveKit Signaling WSS: $lkWsUrl" -ForegroundColor Green

# Step 2: Update .env.local with LiveKit WSS URL
Write-Host "⚙️ Step 2: Updating .env.local in agents-playground..." -ForegroundColor Yellow
$envPath = "$workspace\gateway\livekit\agents-playground\.env.local"
$envContent = Get-Content $envPath -Raw -Encoding UTF8
$envContent = $envContent -replace "NEXT_PUBLIC_LIVEKIT_URL=.*", "NEXT_PUBLIC_LIVEKIT_URL=$lkWsUrl"
Set-Content -Path $envPath -Value $envContent -Encoding UTF8

# Step 3: Restart Next.js Playground to pick up the new env
Write-Host "🔄 Step 3: Restarting Next.js Playground on Port 3005..." -ForegroundColor Yellow
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    $cmd -match "next dev -p 3005"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1
$nodeProc = Start-Process -FilePath "node" -ArgumentList "node_modules/next/dist/bin/next dev -p 3005" -WorkingDirectory "$workspace\gateway\livekit\agents-playground" -PassThru

Start-Sleep -Seconds 3

# Step 4: Start Cloudflare Tunnel for Playground UI (Port 3005)
Write-Host "🌐 Step 4: Starting Cloudflare Tunnel for Agents Playground (Port 3005)..." -ForegroundColor Yellow
$procUi = Start-Process -FilePath "C:\Windows\System32\cloudflared.exe" -ArgumentList "tunnel --url http://127.0.0.1:3005 --logfile `"$uiLog`"" -PassThru

# Wait for Playground URL
$uiUrl = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $uiLog) {
        $content = Get-Content $uiLog -Raw -ErrorAction SilentlyContinue
        if ($content -match "https://([a-zA-Z0-9-]+)\.trycloudflare\.com") {
            $uiUrl = $matches[0]
            break
        }
    }
}

if (-not $uiUrl) {
    Write-Host "❌ Failed to get Playground Tunnel URL." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Playground UI URL: $uiUrl" -ForegroundColor Green

# Save to file
$summary = @"
=====================================================
  🎙️ Maymint LiveKit Public Voice Engine & UI
=====================================================
เข้าใช้งานผ่านอินเทอร์เน็ต (มี HTTPS รองรับไมโครโฟน 100%):

📱 Web UI (เข้าผ่านมือถือ / คอมพิวเตอร์):
   $uiUrl

🔗 LiveKit Signaling WSS:
   $lkWsUrl

🌐 Public Node IP (WebRTC Media UDP/TCP):
   168.222.28.67 (Ports 7881, 7882, 50000-60000)

=====================================================
"@

Set-Content -Path "$workspace\LIVEKIT_PUBLIC_URL.txt" -Value $summary -Encoding UTF8
Write-Host "`n$summary" -ForegroundColor Cyan
