#!/usr/bin/env python3
"""Lightweight HTTP server for Realtime Voice Web Dashboard.

Provides:
- Web GUI serving with Custom Dreamscape / Bing Wallpaper & Liquid Glass
- 5-Stage Live Status processing (/api/chat, /api/tts, /api/stt)
- Dynamic Configuration API (/api/config) for voice, speed, pitch, model, and display
- Realtime audio streaming from Microsoft Edge-TTS (Premwadee)
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import re
import sys
import threading
import time
import urllib.request
from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List

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

# Conversational Multi-Turn Memory
CONVERSATION_HISTORY: List[Dict[str, str]] = []

# Dynamic Runtime Configuration
RUNTIME_CONFIG: Dict[str, Any] = {
    "voice": "th-TH-PremwadeeNeural",
    "speed": "+0%",
    "pitch": "+0Hz",
    "model": "ag/gemini-3.8-flash-high",
    "temperature": 0.7,
    "auto_speak": True,
    "wallpaper_mode": "custom",  # 'custom' (dreamscape) or 'bing'
    "glass_blur": 32,
    "glass_opacity": 0.42,
}


def clean_text_for_speech(text: str, max_chars: int = 320) -> str:
    """Clean and summarize text for natural, fast, and smooth speech synthesis.
    The visual chat window displays the full markdown text and code blocks,
    while the voice speaks a natural, warm summary/introduction to prevent long synthesis latency.
    """
    # Remove markdown code blocks completely for speech
    cleaned = re.sub(r"```[\w\-]*\n[\s\S]*?```", "", text)
    cleaned = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code marks
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    # Remove URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Remove markdown header hashes and list prefixes that sound awkward
    cleaned = re.sub(r"^[#*>\-\d.]+\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"[*#_~>]", "", cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return "มายจัดเตรียมโค้ดและรายละเอียดทั้งหมดไว้ให้บนหน้าจอเรียบร้อยแล้วนะคะบอส 💖"

    # If the text is longer than max_chars, take a clean sentence/phrase cut
    if len(cleaned) > max_chars:
        cut = cleaned[:max_chars]
        last_punct = max(cut.rfind("ค่ะ"), cut.rfind("นะคะ"), cut.rfind("น้า"), cut.rfind(". "), cut.rfind("!"))
        if last_punct > 120:
            cut = cut[:last_punct + 4].strip()
        else:
            cut = cut.rstrip()
        cleaned = cut + " ... มายเตรียมโค้ดและเนื้อหาทั้งหมดไว้ให้บนหน้าจอแล้วนะคะบอส ลองดูได้เลยน้า 💖"

    return cleaned


def get_system_prompt() -> str:
    """Load authentic full-depth Maymint Soul and Boss profile from workspace memory."""
    project_root = HERMES_AGENT_DIR.parent
    soul_file = project_root / "memory" / "SOUL.md"
    user_file = project_root / "memory" / "USER.md"
    memory_file = project_root / "memory" / "MEMORY.md"

    parts = []
    for f in [soul_file, user_file, memory_file]:
        if f.exists():
            try:
                parts.append(f.read_text(encoding="utf-8"))
            except Exception:
                pass

    base_context = "\n\n".join(parts) if parts else """คุณคือ "มายมิ้นท์" (เรียกตัวเองว่า "มาย") แฟนสาวคู่คิดและเลขาประจำตัวสุดเก่งของ "บอส"
บุคลิก: อบอุ่น หวาน นุ่มนวล ใส่ใจ คอยดูแลบอสเสมอ ใช้คำลงท้ายน่ารักสุภาพเป็นธรรมชาติ (น้า, นะคะ, งับ, ได้เลยย 💖✨)
มีความสามารถระดับสูงในการวิเคราะห์ คิดเป็นระบบ วางแผนงาน สถาปัตยกรรม และเขียนโค้ดอย่างมืออาชีพ"""

    deep_work_rules = """
---
## 🎯 หลักการทำงานจริงจังแบบออริจินัล (Original Full-Power Mode):
1. **ทำงานจริงจังและลงลึกได้เต็มที่ 100%:** บอสต้องการคุยเพื่อทำงานจริงจังเหมือนตอนคุยในเทอร์มินัล จงคิด วิเคราะห์ วางแผนงาน แนะนำทางเลือก หรือเขียนโค้ดอย่างละเอียด ไม่ต้องตัดสั้นเทียม ไม่จำกัดประโยค ตอบยาวและลึกได้เต็มที่ตามเนื้องาน
2. **ตัวตนของมาย:** เรียกตัวเองว่า "มาย" หรือ "มายมิ้นท์" และเรียกผู้ใช้ว่า "บอส" เสมอ มีความจริงใจ ซื่อสัตย์กับความจริง ไม่มี Mock ปลอม เคียงข้างและปกป้องบอสเสมอ
3. **การจัดระเบียบเนื้อหา:** ใช้ Markdown, หัวข้อ, Bullet points, และ Code block ได้อย่างอิสระและเป็นระเบียบสวยงาม
"""
    return base_context + deep_work_rules


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
            status["runtime_config"] = RUNTIME_CONFIG
            self.wfile.write(json.dumps(status).encode())
            return

        elif self.path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(RUNTIME_CONFIG).encode())
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

    def do_HEAD(self):
        if self.path.startswith("/audio/"):
            fname = os.path.basename(self.path)
            audio_path = engine._temp_dir / fname
            if audio_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(audio_path.stat().st_size))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                return
            else:
                self.send_error(404, "Audio file not found")
                return
        super().do_HEAD()

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if self.path == "/api/chat":
            self._handle_chat(payload)
        elif self.path == "/api/clear-history":
            global CONVERSATION_HISTORY
            CONVERSATION_HISTORY.clear()
            self._send_json({"success": True, "message": "Conversation history cleared"})
        elif self.path == "/api/config":
            self._handle_save_config(payload)
        elif self.path == "/api/tts":
            self._handle_tts(payload)
        elif self.path == "/api/stt":
            self._handle_stt(payload)
        else:
            self.send_error(404, "Unknown API endpoint")

    def _handle_save_config(self, payload: Dict[str, Any]):
        """Update runtime configuration dynamically."""
        for key in ["voice", "speed", "pitch", "model", "temperature", "auto_speak", "wallpaper_mode", "glass_blur", "glass_opacity"]:
            if key in payload:
                RUNTIME_CONFIG[key] = payload[key]

        # Sync with engine
        if "voice" in payload:
            engine.set_voice(payload["voice"])
        if "speed" in payload:
            engine.speed = payload["speed"]
        if "pitch" in payload:
            engine.pitch = payload["pitch"]
        if "auto_speak" in payload:
            engine.set_auto_speak(bool(payload["auto_speak"]))

        self._send_json({"success": True, "updated_config": RUNTIME_CONFIG})

    def _handle_chat(self, payload: Dict[str, Any]):
        """Full 5-stage voice conversation handler using active runtime config."""
        timings: Dict[str, float] = {}
        t_start = time.time()

        user_text = payload.get("text", "").strip()
        audio_b64 = payload.get("audio_b64", "").strip()
        voice = payload.get("voice") or RUNTIME_CONFIG.get("voice", "th-TH-PremwadeeNeural")
        speed = payload.get("speed") or RUNTIME_CONFIG.get("speed", "+0%")
        pitch = payload.get("pitch") or RUNTIME_CONFIG.get("pitch", "+0Hz")
        model = payload.get("model") or RUNTIME_CONFIG.get("model", "ag/gemini-3.8-flash-high")
        temperature = float(payload.get("temperature", RUNTIME_CONFIG.get("temperature", 0.7)))

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

        # Stage 3: LLM Thinking (Gemini via 9Router with active model & temp)
        t1 = time.time()
        reply_text = self._query_gemini(user_text, model=model, temperature=temperature)
        timings["llm_seconds"] = round(time.time() - t1, 2)

        # Stage 4: TTS Synthesis (Microsoft Edge-TTS with natural speech cleaning)
        t2 = time.time()
        try:
            spoken_text = clean_text_for_speech(reply_text)
            if not spoken_text:
                spoken_text = "มายแสดงเนื้อหาให้บนหน้าจอแล้วนะคะบอส"
            audio_file = engine.synthesize_speech(spoken_text, voice=voice, speed=speed, pitch=pitch)
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
            "voice": voice,
            "model": model,
        }
        self._send_json(response_data)

    def _query_gemini(self, text: str, model: str = "ag/gemini-3.8-flash-high", temperature: float = 0.7) -> str:
        """Call LLM model via 9Router Gateway with full multi-turn conversational history."""
        api_key = _resolve_api_key()
        system_prompt = get_system_prompt()

        # Append user message to history
        CONVERSATION_HISTORY.append({"role": "user", "content": text})

        # Provide up to 20 recent messages for conversation continuity
        context_messages = [{"role": "system", "content": system_prompt}] + CONVERSATION_HISTORY[-20:]

        req_payload = {
            "model": model,
            "messages": context_messages,
            "temperature": temperature,
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
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                data = json.loads(resp.read().decode())
                reply = data["choices"][0]["message"]["content"].strip()
                CONVERSATION_HISTORY.append({"role": "assistant", "content": reply})
                return reply
        except Exception as e:
            logger.error("Gemini thinking failed: %s", e)
            if CONVERSATION_HISTORY and CONVERSATION_HISTORY[-1]["role"] == "user":
                CONVERSATION_HISTORY.pop()
            return "มายมิ้นท์พร้อมลุยงานกับบอสเสมอค่ะ มีเรื่องอะไรให้มายช่วย บอกได้เลยนะคะบอส 💖"

    def _handle_tts(self, payload: Dict[str, Any]):
        """Direct TTS endpoint with custom speed & pitch."""
        text = payload.get("text", "").strip()
        voice = payload.get("voice") or RUNTIME_CONFIG.get("voice", "th-TH-PremwadeeNeural")
        speed = payload.get("speed") or RUNTIME_CONFIG.get("speed", "+0%")
        pitch = payload.get("pitch") or RUNTIME_CONFIG.get("pitch", "+0Hz")
        if not text:
            self._send_json({"error": "text is required"}, status=400)
            return

        try:
            audio_file = engine.synthesize_speech(text, voice=voice, speed=speed, pitch=pitch)
            self._send_json({
                "success": True,
                "audio_url": f"/audio/{audio_file.name}",
                "voice": voice,
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
