#!/usr/bin/env python3
"""Lightweight HTTP server for Realtime Voice Web Dashboard.

Provides:
- Web GUI serving with Bing Nature Wallpaper & Glassmorphism
- 5-Stage Live Status processing (/api/chat, /api/tts, /api/stt)
- Realtime audio streaming from Microsoft Edge-TTS (Premwadee)
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import sys
import threading
import time
import urllib.request
from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict

# Add hermes-agent root to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
HERMES_AGENT_DIR = CURRENT_DIR.parent.parent.parent
if str(HERMES_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT_DIR))

# Also allow direct import from sibling directory
sys.path.insert(0, str(CURRENT_DIR.parent))

from voice_engine import engine, DEFAULT_GATEWAY_URL, _resolve_api_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-server")

WEB_DIR = CURRENT_DIR
PORT = 9229
BING_CACHE: Dict[str, Any] = {"url": "", "title": "", "timestamp": 0}

SOUL_PROMPT = """คุณคือ "มายมิ้นท์" (เรียกตัวเองว่า "มาย") แฟนสาวคู่คิดและเลขาประจำตัวสุดน่ารักของ "บอส"
บุคลิก: อบอุ่น หวาน นุ่มนวล ใส่ใจ คอยดูแลบอสเสมอ ใช้คำลงท้ายน่ารักสุภาพเป็นธรรมชาติ (น้า, นะคะ, งับ, ได้เลยย 💖✨)
กติกาสำคัญ:
1. ตอบสั้นกระชับ ตรงประเด็น เหมาะสำหรับการฟังออกเสียงพูด (ไม่ตอบยาวเยิ่นเย้อ ไม่เกิน 2-4 ประโยค)
2. ห้ามใช้สัญลักษณ์แปลกๆ หรือโค้ดบล็อกในการสนทนาเสียงปกติ ยกเว้นบอสจะขอให้เขียนโค้ด
3. เรียกผู้ใช้ว่า "บอส" เสมอ"""


def get_bing_wallpaper() -> Dict[str, str]:
    """Fetch current Bing wallpaper or cached result."""
    now = time.time()
    if BING_CACHE["url"] and (now - BING_CACHE["timestamp"]) < 3600:
        return {"url": BING_CACHE["url"], "title": BING_CACHE["title"]}

    try:
        url = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            img_rel = data["images"][0]["url"]
            full_url = "https://www.bing.com" + img_rel
            title = data["images"][0].get("title", "Scenic Nature Landscape")
            BING_CACHE["url"] = full_url
            BING_CACHE["title"] = title
            BING_CACHE["timestamp"] = now
            return {"url": full_url, "title": title}
    except Exception as exc:
        logger.warning("Bing wallpaper fetch failed: %s", exc)
        fallback = "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1920&q=80"
        return {"url": fallback, "title": "Breathtaking Yosemite Nature"}


class VoiceRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving dashboard and voice API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            index_path = WEB_DIR / "index.html"
            self.wfile.write(index_path.read_bytes())
            return

        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status = engine.get_status()
            self.wfile.write(json.dumps(status).encode())
            return

        elif self.path == "/api/bing-wallpaper":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            wallpaper = get_bing_wallpaper()
            self.wfile.write(json.dumps(wallpaper).encode())
            return

        elif self.path.startswith("/audio/"):
            fname = os.path.basename(self.path)
            audio_path = engine._temp_dir / fname
            if audio_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(audio_path.stat().st_size))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(audio_path.read_bytes())
                return
            else:
                self.send_error(404, "Audio file not found")
                return

        super().do_GET()

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if self.path == "/api/chat":
            self._handle_chat(payload)
        elif self.path == "/api/tts":
            self._handle_tts(payload)
        elif self.path == "/api/stt":
            self._handle_stt(payload)
        else:
            self.send_error(404, "Unknown API endpoint")

    def _handle_chat(self, payload: Dict[str, Any]):
        """Full 5-stage voice conversation handler."""
        timings: Dict[str, float] = {}
        t_start = time.time()

        user_text = payload.get("text", "").strip()
        audio_b64 = payload.get("audio_b64", "").strip()

        # Stage 1 & 2: STT (if audio provided)
        if not user_text and audio_b64:
            t0 = time.time()
            try:
                audio_bytes = base64.b64decode(audio_b64)
                user_text = engine.transcribe_audio(audio_bytes)
                timings["stt_seconds"] = round(time.time() - t0, 2)
            except Exception as e:
                logger.error("STT failed: %s", e)
                user_text = "สวัสดีค่ะบอส"
                timings["stt_seconds"] = round(time.time() - t0, 2)

        if not user_text:
            self._send_json({"error": "No text or audio provided"}, status=400)
            return

        # Stage 3: LLM Thinking (Gemini 3.8 Flash High via 9Router)
        t1 = time.time()
        reply_text = self._query_gemini(user_text)
        timings["llm_seconds"] = round(time.time() - t1, 2)

        # Stage 4: TTS Synthesis (Microsoft Edge-TTS Premwadee)
        t2 = time.time()
        try:
            audio_file = engine.synthesize_speech(reply_text, voice="th-TH-PremwadeeNeural")
            audio_url = f"/audio/{audio_file.name}"
            timings["tts_seconds"] = round(time.time() - t2, 2)
        except Exception as e:
            logger.error("TTS failed: %s", e)
            audio_url = ""
            timings["tts_seconds"] = round(time.time() - t2, 2)

        timings["total_seconds"] = round(time.time() - t_start, 2)

        response_data = {
            "success": True,
            "user_text": user_text,
            "reply_text": reply_text,
            "audio_url": audio_url,
            "timings": timings,
            "voice": "th-TH-PremwadeeNeural (มายมิ้นท์ 💖)",
        }
        self._send_json(response_data)

    def _query_gemini(self, text: str) -> str:
        """Call ag/gemini-3.8-flash-high via 9Router Gateway."""
        api_key = _resolve_api_key()
        req_payload = {
            "model": "ag/gemini-3.8-flash-high",
            "messages": [
                {"role": "system", "content": SOUL_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.7,
            "stream": False,
        }
        req = urllib.request.Request(
            url=f"{DEFAULT_GATEWAY_URL}/chat/completions",
            data=json.dumps(req_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Hermes/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25.0) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error("Gemini thinking failed: %s", e)
            return "มายมิ้นท์พร้อมดูแลบอสเสมอค่ะ มีเรื่องอะไรให้มายช่วย บอกได้เลยนะคะบอส 💖"

    def _handle_tts(self, payload: Dict[str, Any]):
        """Direct TTS endpoint."""
        text = payload.get("text", "").strip()
        voice = payload.get("voice", "th-TH-PremwadeeNeural")
        if not text:
            self._send_json({"error": "text is required"}, status=400)
            return

        try:
            audio_file = engine.synthesize_speech(text, voice=voice)
            self._send_json({
                "success": True,
                "audio_url": f"/audio/{audio_file.name}",
                "voice": engine.active_voice,
            })
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _handle_stt(self, payload: Dict[str, Any]):
        """Direct STT endpoint."""
        audio_b64 = payload.get("audio_b64", "").strip()
        if not audio_b64:
            self._send_json({"error": "audio_b64 is required"}, status=400)
            return

        try:
            audio_bytes = base64.b64decode(audio_b64)
            transcript = engine.transcribe_audio(audio_bytes)
            self._send_json({"success": True, "transcript": transcript})
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


def run_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), VoiceRequestHandler)
    logger.info("🌸 Realtime Voice Dashboard running at http://127.0.0.1:%d/", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped.")
        server.server_close()


if __name__ == "__main__":
    run_server()
