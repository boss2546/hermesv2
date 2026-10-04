@echo off
title Cloudflare Custom Domain Setup - Hermes v2
cd /d "%~dp0"
echo =======================================================================
echo     🌐 เชื่อมต่อ Cloudflare Tunnel กับ Custom Domain ของคุณ
echo =======================================================================
echo.
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0scripts\run-custom-tunnel.ps1"
pause
