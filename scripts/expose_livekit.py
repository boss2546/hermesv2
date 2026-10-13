#!/usr/bin/env python3
"""Expose LiveKit Voice Engine and Agents Playground via Cloudflare Tunnels."""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

WORKSPACE = Path(__file__).resolve().parent.parent
SCRATCH = WORKSPACE / "scratch"
SCRATCH.mkdir(exist_ok=True)

LK_LOG = SCRATCH / "livekit-tunnel.log"
UI_LOG = SCRATCH / "playground-tunnel.log"

def cleanup_file(path: Path):
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass

def wait_for_tunnel_url(log_file: Path, timeout: int = 30) -> str | None:
    regex = re.compile(r"https://([a-zA-Z0-9-]+)\.trycloudflare\.com")
    start = time.time()
    while time.time() - start < timeout:
        if log_file.exists():
            try:
                content = log_file.read_text(encoding="utf-8", errors="ignore")
                match = regex.search(content)
                if match:
                    return match.group(0)
            except Exception:
                pass
        time.sleep(1)
    return None

def main():
    cleanup_file(LK_LOG)
    cleanup_file(UI_LOG)

    print("🌐 [1/4] Starting Cloudflare Tunnel for LiveKit Signaling (Port 7880)...")
    proc_lk = subprocess.Popen(
        ["cloudflared.exe", "tunnel", "--url", "http://127.0.0.1:7880", "--logfile", str(LK_LOG)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )

    lk_url = wait_for_tunnel_url(LK_LOG)
    if not lk_url:
        print("❌ Failed to get LiveKit Tunnel URL.")
        proc_lk.terminate()
        sys.exit(1)

    lk_wss = lk_url.replace("https://", "wss://")
    print(f"✅ LiveKit Signaling WSS: {lk_wss}")

    print("⚙️ [2/4] Updating .env.local with LiveKit WSS URL...")
    env_file = WORKSPACE / "gateway" / "livekit" / "agents-playground" / ".env.local"
    env_content = env_file.read_text(encoding="utf-8")
    env_content = re.sub(
        r"NEXT_PUBLIC_LIVEKIT_URL=.*",
        f"NEXT_PUBLIC_LIVEKIT_URL={lk_wss}",
        env_content
    )
    env_file.write_text(env_content, encoding="utf-8")

    print("🔄 [3/4] Restarting Next.js Playground to load new WSS URL...")
    # Kill existing Next.js dev server on 3005 if running
    try:
        subprocess.run(
            ["powershell.exe", "-Command", "Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { (Get-CimInstance Win32_Process -Filter \"ProcessId = $($_.Id)\").CommandLine -match '3005' } | Stop-Process -Force"],
            capture_output=True
        )
    except Exception:
        pass

    time.sleep(1)
    proc_next = subprocess.Popen(
        ["node", "node_modules/next/dist/bin/next", "dev", "-p", "3005"],
        cwd=str(WORKSPACE / "gateway" / "livekit" / "agents-playground"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    time.sleep(4)

    print("🌐 [4/4] Starting Cloudflare Tunnel for Agents Playground (Port 3005)...")
    proc_ui = subprocess.Popen(
        ["cloudflared.exe", "tunnel", "--url", "http://127.0.0.1:3005", "--logfile", str(UI_LOG)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )

    ui_url = wait_for_tunnel_url(UI_LOG)
    if not ui_url:
        print("❌ Failed to get Playground Tunnel URL.")
        sys.exit(1)

    print(f"✅ Playground UI URL: {ui_url}")

    summary = f"""=====================================================
  🎙️ Maymint LiveKit Public Voice Engine & UI
=====================================================
เข้าใช้งานผ่านอินเทอร์เน็ต (มี HTTPS รองรับไมโครโฟน 100%):

📱 Web UI (เข้าผ่านมือถือ / คอมพิวเตอร์):
   {ui_url}

🔗 LiveKit Signaling WSS:
   {lk_wss}

🌐 Public Node IP (WebRTC Media UDP/TCP):
   168.222.28.67 (Ports 7881, 7882, 50000-60000)

=====================================================
"""
    result_file = WORKSPACE / "LIVEKIT_PUBLIC_URL.txt"
    result_file.write_text(summary, encoding="utf-8")
    print("\n" + summary)

if __name__ == "__main__":
    main()
