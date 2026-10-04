@echo off
title Cloudflare Tunnel Launcher - Hermes v2
cd /d "%~dp0"
echo =======================================================================
echo        🌐 เปิดใช้งาน Cloudflare Tunnel (ส่งออกเน็ตผ่าน HTTPS)
echo =======================================================================
echo.
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0scripts\run-tunnel.ps1"
pause
