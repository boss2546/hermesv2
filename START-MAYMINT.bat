@echo off
title Maymint LiveKit 24/7 Supervisor - Hermes v2
cd /d "%~dp0"
echo =======================================================================
echo    🌸 Maymint Liquid Voice & LiveKit 24/7 Supervisor
echo =======================================================================
echo.
echo Starting 24/7 Watchdog Supervisor...
echo Services managed:
echo  1. LiveKit WebRTC Server (Port 7880, 7881, 50000-50100)
echo  2. Maymint Voice Agent Daemon (Gemini + Edge-TTS + Silero VAD)
echo  3. Maymint Liquid Glass Dashboard (Port 9229, PIN Secured)
echo.
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0scripts\maymint-watchdog.ps1"
pause
