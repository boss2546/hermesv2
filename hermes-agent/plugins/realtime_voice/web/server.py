#!/usr/bin/env python3
"""Unified HTTP Server for Maymint Dashboard & LiveKit Voice Integration.

Provides:
- Web GUI serving with Liquid Glass Aesthetic, PIN Security (4-digit lockout protection)
- LiveKit WebRTC JWT token generation (/api/livekit-token)
- Background Jobs Management & SSE event streaming (/api/jobs, /api/jobs/stream)
- Dual-Mode Cognitive Chat endpoint (/api/chat) powered by maymint_brain
- Multi-session persistence and Knowledge Lexicon management
- Microsoft Edge-TTS streaming playback
"""

from __future__ import annotations

import os
import sys

# Fast Singleton Mutex Check before loading web framework
if os.name == "nt":
    import ctypes
    _kernel32 = ctypes.windll.kernel32
    _server_mutex = _kernel32.CreateMutexW(None, False, "Global\\MaymintWebServerMutex")
    if _kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("⚠️ Another Maymint Web Server instance is already active. Exiting safely.", flush=True)
        sys.exit(0)

import base64
import json
import logging
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Path discovery
CURRENT_DIR = Path(__file__).resolve().parent
HERMES_AGENT_DIR = CURRENT_DIR.parent.parent.parent
PROJECT_ROOT = HERMES_AGENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(HERMES_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT_DIR))
if str(CURRENT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR.parent))

# Import Maymint Central Brain
try:
    import maymint_brain
except Exception as e:
    logging.warning("Could not import maymint_brain: %s", e)
    maymint_brain = None

# Import LiveKit API for JWT token minting
try:
    from livekit.api import AccessToken, VideoGrants
except Exception as e:
    logging.warning("Could not import livekit.api: %s", e)
    AccessToken, VideoGrants = None, None

try:
    from voice_engine import DEFAULT_GATEWAY_URL, engine
except Exception:
    engine = None
    DEFAULT_GATEWAY_URL = "https://api.meuu.club/v1"

try:
    from knowledge_lexicon import lexicon_mgr
except Exception:
    lexicon_mgr = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-server")

WEB_DIR = CURRENT_DIR
PORT = 9229
AUDIO_CACHE_DIR = PROJECT_ROOT / "cache" / "audio"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
BING_CACHE: Dict[str, Any] = {"url": "", "title": "", "timestamp": 0}

# =============================================================================
# 1. PIN SECURITY & SESSION AUTHENTICATION
# =============================================================================

MAYMINT_PIN = maymint_brain.MAYMINT_PIN if maymint_brain else "2546"
AUTH_FILE = CURRENT_DIR.parent / ".auth_tokens.json"

def _load_valid_tokens() -> Set[str]:
    if AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return set(data)
        except Exception:
            pass
    return set()

def _save_valid_tokens(tokens: Set[str]):
    try:
        AUTH_FILE.write_text(json.dumps(list(tokens), ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.error("Could not save auth tokens: %s", e)

VALID_TOKENS: Set[str] = _load_valid_tokens()
FAILED_ATTEMPTS: Dict[str, List[Any]] = {}  # ip: [count, last_time]
_auth_lock = threading.RLock()

# Dynamic Runtime Configuration
CONFIG_TXT_PATH = CURRENT_DIR.parent / "config.txt"
CONFIG_PATH = HERMES_AGENT_DIR.parent / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "voice": "th-TH-PremwadeeNeural",
    "speed": "+0%",
    "pitch": "+0Hz",
    "model": "auto",
    "temperature": 0.7,
    "auto_speak": True,
    "wallpaper_mode": "custom",
    "glass_blur": 32,
    "glass_opacity": 0.42,
    "enable_terminal_tools": True,
    "command_timeout": 120,
    "custom_prompt": ""
}

def load_stored_config() -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if not k.startswith("comment_"):
                        cfg[k] = v
        except Exception as e:
            logger.warning("Could not read config.json: %s", e)
    return cfg

RUNTIME_CONFIG: Dict[str, Any] = load_stored_config()

def save_stored_config(cfg: Dict[str, Any]):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Could not save config.json: %s", e)

# Bing Wallpaper Helper
def get_bing_wallpaper() -> Dict[str, str]:
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
        fallback = "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1920&q=80"
        return {"url": fallback, "title": "Breathtaking Yosemite Nature"}

# =============================================================================
# 2. HTTP REQUEST HANDLER
# =============================================================================

class VoiceRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _check_auth(self) -> bool:
        """Verifies 30-day authenticated session cookie or header token."""
        # 1. Header token check
        auth_header = self.headers.get("X-Maymint-Key") or self.headers.get("Authorization")
        if auth_header:
            token = auth_header.replace("Bearer ", "").strip()
            if token in VALID_TOKENS:
                return True

        # 2. Cookie check
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            try:
                cookies = SimpleCookie(cookie_header)
                if "maymint_auth" in cookies:
                    c_token = cookies["maymint_auth"].value
                    if c_token in VALID_TOKENS:
                        return True
            except Exception:
                pass

        # 3. Query string token check
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        q_token = qs.get("auth_token", [""])[0]
        if q_token and q_token in VALID_TOKENS:
            return True

        return False

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Static assets accessible without auth
        if path == "/" or path.startswith("/?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            index_path = WEB_DIR / "index.html"
            self.wfile.write(index_path.read_bytes())
            return

        elif path == "/background.jpg" or path.endswith(".png") or path.endswith(".jpg") or path.endswith(".ico"):
            super().do_GET()
            return

        elif path.startswith("/audio/"):
            self._serve_audio(is_head=False)
            return

        # Public auth check endpoint
        elif path == "/api/auth/check":
            is_authed = self._check_auth()
            self._send_json({"authenticated": is_authed})
            return

        elif path == "/api/bing-wallpaper":
            wallpaper = get_bing_wallpaper()
            self._send_json(wallpaper)
            return

        # ALL OTHER API ENDPOINTS REQUIRE PIN AUTHENTICATION!
        if not self._check_auth():
            self._send_json({
                "error": "unauthorized",
                "message": "กรุณาใส่รหัส PIN 4 หลักเพื่อเข้าใช้งานค่ะบอส 💖"
            }, status=401)
            return

        # Authenticated endpoints
        if path == "/api/status":
            status = engine.get_status() if engine else {"status": "ready"}
            status["runtime_config"] = RUNTIME_CONFIG
            status["pin_secured"] = True
            self._send_json(status)
            return

        elif path == "/api/config":
            self._send_json(RUNTIME_CONFIG)
            return

        elif path == "/api/history":
            history = maymint_brain.load_chat_history() if maymint_brain else []
            self._send_json({"success": True, "history": history})
            return

        elif path == "/api/sessions":
            active_sid = maymint_brain.get_active_session_id() if maymint_brain else "default"
            sessions = []
            if maymint_brain:
                for p in maymint_brain.SESSIONS_DIR.glob("session_*.json"):
                    try:
                        s_data = json.loads(p.read_text(encoding="utf-8"))
                        sessions.append({
                            "id": s_data.get("id", p.stem),
                            "title": s_data.get("title", "บทสนทนา"),
                            "created_at": s_data.get("created_at", int(p.stat().st_mtime)),
                            "updated_at": s_data.get("updated_at", int(p.stat().st_mtime)),
                            "message_count": len(s_data.get("messages", []))
                        })
                    except Exception:
                        pass
                sessions.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
            self._send_json({"success": True, "active_session_id": active_sid, "sessions": sessions})
            return

        elif path == "/api/livekit-token":
            # LiveKit WebRTC AccessToken Minting
            qs = urllib.parse.parse_qs(parsed.query)
            identity = qs.get("identity", ["Boss"])[0]
            room = qs.get("room", ["maymint-room"])[0]

            api_key = maymint_brain.ENV_VARS.get("LIVEKIT_API_KEY", "maymint_key_bcf1fe4a923e6181") if maymint_brain else "devkey"
            api_secret = maymint_brain.ENV_VARS.get("LIVEKIT_API_SECRET", "maymint_sec_0d4cedaee574e28e5d5cf90fb8c81e4c") if maymint_brain else "secret"
            public_url = maymint_brain.ENV_VARS.get("LIVEKIT_PUBLIC_URL", "wss://lk.meuu.live") if maymint_brain else "ws://localhost:7880"

            if AccessToken and VideoGrants:
                token = AccessToken(api_key=api_key, api_secret=api_secret)
                token.with_identity(identity).with_name(identity).with_grants(
                    VideoGrants(
                        room_join=True,
                        room=room,
                        can_publish=True,
                        can_subscribe=True,
                        can_publish_data=True
                    )
                )
                jwt_token = token.to_jwt()
            else:
                jwt_token = "mock_token"

            self._send_json({
                "token": jwt_token,
                "url": public_url,
                "fallback_url": "ws://127.0.0.1:7880",
                "room": room,
                "identity": identity
            })
            return

        elif path == "/api/jobs":
            qs = urllib.parse.parse_qs(parsed.query)
            lim = int(qs.get("limit", [200])[0])
            jobs = maymint_brain.job_manager.get_all(limit=lim) if maymint_brain else []
            metrics = maymint_brain.job_manager.get_metrics() if maymint_brain else {}
            self._send_json({"success": True, "jobs": jobs, "metrics": metrics})
            return

        elif path == "/api/jobs/metrics":
            metrics = maymint_brain.job_manager.get_metrics() if maymint_brain else {}
            self._send_json({"success": True, "metrics": metrics})
            return

        elif path == "/api/jobs/stream":
            # Server-Sent Events (SSE) for Real-time Job Progress
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            stop_event = threading.Event()

            def _listener(job_data):
                try:
                    payload = f"data: {json.dumps(job_data, ensure_ascii=False)}\n\n"
                    self.wfile.write(payload.encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    stop_event.set()

            if maymint_brain:
                maymint_brain.job_manager.add_sync_listener(_listener)

            try:
                # Keep stream open with periodic keep-alive heartbeat to detect broken socket
                while not stop_event.is_set():
                    if stop_event.wait(timeout=5.0):
                        break
                    try:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                    except Exception:
                        stop_event.set()
                        break
            finally:
                if maymint_brain:
                    maymint_brain.job_manager.remove_sync_listener(_listener)
            return

        elif path == "/api/lexicon":
            lex_data = lexicon_mgr.get_all() if lexicon_mgr else {}
            stats = lexicon_mgr.get_summary_stats() if lexicon_mgr else {}
            self._send_json({"success": True, "lexicon": lex_data, "stats": stats})
            return

        super().do_GET()

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len > 10 * 1024 * 1024:
            self._send_json({"error": "payload_too_large", "message": "Payload exceeds 10MB limit"}, status=413)
            return

        body = self.rfile.read(content_len)
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        path = self.path

        # 1. PIN Authentication Endpoint (Public)
        if path == "/api/auth/pin":
            self._handle_pin_auth(payload)
            return

        # All subsequent endpoints require authentication
        if not self._check_auth():
            self._send_json({
                "error": "unauthorized",
                "message": "กรุณาใส่รหัส PIN 4 หลักค่ะบอส"
            }, status=401)
            return

        # Authenticated endpoints
        if path == "/api/chat":
            self._handle_chat(payload)
        elif path == "/api/voice/process":
            self._handle_voice_process(payload)
        elif path == "/api/voice/transcribe":
            self._handle_voice_transcribe(payload)
        elif path == "/api/jobs/submit":
            if not maymint_brain:
                self._send_json({"error": "Maymint Brain not loaded"}, status=500)
                return
            j_name = payload.get("name", "งานระบบเบื้องหลัง")
            j_type = payload.get("job_type", "command")
            desc = payload.get("description", "")
            dev_lock = payload.get("device_lock_key")

            if j_type == "command" or "command" in payload:
                cmd = payload.get("command", "")
                job = maymint_brain.job_manager.submit(
                    name=j_name,
                    func=maymint_brain.execute_tool,
                    args=("run_terminal_command", {"command": cmd, "cwd": payload.get("cwd", ".")}),
                    device_lock_key=dev_lock,
                    description=desc or f"คำสั่ง: {cmd[:50]}",
                    on_complete_summary=lambda r: f"งาน {j_name} เสร็จแล้วค่ะ"
                )
                self._send_json({"success": True, "status": "submitted", "job_id": job.id, "job": asdict(job)})
            elif j_type == "python" or "code" in payload:
                code = payload.get("code", "")
                job = maymint_brain.job_manager.submit(
                    name=j_name,
                    func=maymint_brain.execute_tool,
                    args=("execute_python_code", {"code": code}),
                    device_lock_key=dev_lock,
                    description=desc or "Python Script",
                    on_complete_summary=lambda r: f"งาน {j_name} รันเสร็จแล้วค่ะ"
                )
                self._send_json({"success": True, "status": "submitted", "job_id": job.id, "job": asdict(job)})
            else:
                self._send_json({"error": "Either command or code required"}, status=400)
        elif path == "/api/jobs/cancel":
            job_id = payload.get("job_id", "")
            ok = maymint_brain.job_manager.cancel(job_id) if maymint_brain else False
            self._send_json({"success": ok, "job_id": job_id})
        elif path == "/api/config":
            self._handle_save_config(payload)
        elif path == "/api/tts":
            self._handle_tts(payload)
        elif path == "/api/clear-history":
            if maymint_brain:
                maymint_brain.save_chat_history([])
            self._send_json({"success": True})
        elif path == "/api/sessions/new":
            if maymint_brain:
                new_id = f"session_{int(time.time())}"
                maymint_brain.set_active_session_id(new_id)
                maymint_brain.save_chat_history([])
            self._send_json({"success": True, "active_session_id": maymint_brain.get_active_session_id() if maymint_brain else ""})
        elif path == "/api/sessions/switch":
            sid = payload.get("session_id", "").strip()
            if maymint_brain:
                s_file = maymint_brain.SESSIONS_DIR / f"{sid}.json"
                if s_file.exists():
                    s_data = json.loads(s_file.read_text(encoding="utf-8"))
                    maymint_brain.set_active_session_id(sid)
                    maymint_brain.save_chat_history(s_data.get("messages", []))
                    self._send_json({"success": True, "active_session_id": sid, "history": s_data.get("messages", [])})
                    return
            self._send_json({"error": "Session not found"}, status=404)
        elif path == "/api/lexicon/add":
            if lexicon_mgr:
                item = lexicon_mgr.add_or_update_item(
                    category=payload.get("category", "commands"),
                    term=payload.get("term", ""),
                    aliases=payload.get("aliases", []),
                    desc=payload.get("desc", "")
                )
                self._send_json({"success": True, "item": item})
                return
            self._send_json({"error": "Lexicon not loaded"}, status=500)
        else:
            self._send_json({"error": "Unknown API endpoint"}, status=404)

    def _handle_pin_auth(self, payload: Dict[str, Any]):
        """Processes 4-digit PIN verification with 5-attempt/15-minute lockout and constant-time check."""
        client_ip = (
            self.headers.get("CF-Connecting-IP")
            or self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or self.client_address[0]
        )
        now = time.time()

        with _auth_lock:
            fail_info = FAILED_ATTEMPTS.get(client_ip, [0, 0])
            if fail_info[0] >= 5 and (now - fail_info[1]) < 900:
                wait_sec = int(900 - (now - fail_info[1]))
                self._send_json({
                    "success": False,
                    "locked": True,
                    "message": f"ใส่รหัสผิดเกิน 5 ครั้ง ระบบล็อกชั่วคราว กรุณารออีก {wait_sec} วินาทีค่ะบอส 🥺"
                }, status=429)
                return

            pin_in = str(payload.get("pin", "")).strip()
            if secrets.compare_digest(pin_in, str(MAYMINT_PIN)):
                FAILED_ATTEMPTS.pop(client_ip, None)
                token = secrets.token_hex(24)
                VALID_TOKENS.add(token)
                _save_valid_tokens(VALID_TOKENS)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Set-Cookie", f"maymint_auth={token}; Path=/; Max-Age=2592000; SameSite=Lax")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "token": token,
                    "message": "ยินดีต้อนรับกลับบ้านค่ะบอส 💖 น้องมายพร้อมดูแลบอสแล้วค่ะ"
                }, ensure_ascii=False).encode("utf-8"))
            else:
                fail_info[0] += 1
                fail_info[1] = now
                FAILED_ATTEMPTS[client_ip] = fail_info
                rem = max(0, 5 - fail_info[0])
                self._send_json({
                    "success": False,
                    "message": f"รหัส PIN ไม่ถูกต้องค่ะบอส (เหลือโอกาสอีก {rem} ครั้ง)",
                    "remaining_attempts": rem
                }, status=401)

    def _handle_chat(self, payload: Dict[str, Any]):
        """Dual-Mode Cognitive Chat completion via maymint_brain."""
        user_text = (payload.get("text") or payload.get("message") or "").strip()
        mode = payload.get("mode", "casual")
        voice = payload.get("voice") or RUNTIME_CONFIG.get("voice", "th-TH-PremwadeeNeural")
        speed = payload.get("speed") or RUNTIME_CONFIG.get("speed", "+0%")
        pitch = payload.get("pitch") or RUNTIME_CONFIG.get("pitch", "+0Hz")
        auto_speak = payload.get("auto_speak", RUNTIME_CONFIG.get("auto_speak", True))

        if not user_text:
            self._send_json({"error": "text is required"}, status=400)
            return

        if not maymint_brain:
            self._send_json({"error": "Maymint Brain not initialized"}, status=500)
            return

        try:
            # Execute chat turn through unified Maymint Brain
            turn_result = maymint_brain.execute_chat_turn(user_text=user_text, mode=mode)
            clean_speech = turn_result.get("speech_text", "")

            audio_url = None
            if auto_speak and clean_speech:
                try:
                    f_path, chunks, dur = synthesize_speech_multiround(clean_speech, voice=voice, speed=speed, pitch=pitch)
                    audio_url = f"/audio/{f_path.name}"
                except Exception as tts_e:
                    logger.warning("TTS generation warning: %s", tts_e)

            response_data = {
                "success": True,
                "reply": turn_result.get("text", ""),
                "speech_text": clean_speech,
                "audio_url": audio_url,
                "tool_events": turn_result.get("tool_events", []),
                "cognitive_tier": turn_result.get("cognitive_tier", "fast"),
                "model_used": turn_result.get("model_used", "ag/gemini-2.5-flash"),
                "mode": mode
            }
            self._send_json(response_data)

        except Exception as e:
            logger.error("Chat completion error: %s", e)
            self._send_json({"error": str(e)}, status=500)

    def _handle_voice_process(self, payload: Dict[str, Any]):
        """Processes recorded audio from browser: STT Transcription -> LLM Brain -> TTS Speech."""
        audio_b64 = payload.get("audio_base64") or payload.get("audio") or ""
        mode = payload.get("mode", "casual")
        voice = payload.get("voice") or RUNTIME_CONFIG.get("voice", "th-TH-PremwadeeNeural")
        speed = payload.get("speed") or RUNTIME_CONFIG.get("speed", "+0%")
        pitch = payload.get("pitch") or RUNTIME_CONFIG.get("pitch", "+0Hz")
        auto_speak = payload.get("auto_speak", RUNTIME_CONFIG.get("auto_speak", True))

        if not audio_b64:
            self._send_json({"error": "audio_base64 is required"}, status=400)
            return

        if not engine:
            self._send_json({"error": "VoiceEngine not initialized"}, status=500)
            return

        try:
            # Strip data URL prefix if present (e.g. data:audio/webm;base64,...)
            if "," in audio_b64:
                audio_b64 = audio_b64.split(",", 1)[1]
            audio_bytes = base64.b64decode(audio_b64)

            # Step 1: Speech-to-Text via 9Router Multimodal Gemini 2.5 Flash
            t_start = time.time()
            transcript = engine.transcribe_audio(audio_bytes)
            stt_duration = round(time.time() - t_start, 2)
            logger.info("Transcribed audio (%d bytes) in %.2fs: '%s'", len(audio_bytes), stt_duration, transcript)

            if not transcript or not transcript.strip():
                self._send_json({
                    "success": False,
                    "transcript": "",
                    "message": "ไม่สามารถตรวจจับเสียงพูดได้ชัดเจนค่ะบอส กรุณาลองพูดอีกครั้งนะคะ 🥺",
                    "stt_duration": stt_duration
                })
                return

            # Step 2: Cognitive Chat Turn via Unified Maymint Brain
            turn_result = maymint_brain.execute_chat_turn(user_text=transcript, mode=mode)
            clean_speech = turn_result.get("speech_text", "")

            # Step 3: Text-to-Speech synthesis
            audio_url = None
            if auto_speak and clean_speech:
                try:
                    f_path, chunks, dur = synthesize_speech_multiround(clean_speech, voice=voice, speed=speed, pitch=pitch)
                    audio_url = f"/audio/{f_path.name}"
                except Exception as tts_e:
                    logger.warning("Voice TTS generation warning: %s", tts_e)

            response_data = {
                "success": True,
                "transcript": transcript,
                "stt_duration": stt_duration,
                "reply": turn_result.get("text", ""),
                "speech_text": clean_speech,
                "audio_url": audio_url,
                "tool_events": turn_result.get("tool_events", []),
                "cognitive_tier": turn_result.get("cognitive_tier", "fast"),
                "model_used": turn_result.get("model_used", "ag/gemini-2.5-flash"),
                "mode": mode
            }
            self._send_json(response_data)

        except Exception as e:
            logger.error("Voice processing error: %s", e)
            self._send_json({"error": str(e), "message": f"เกิดข้อผิดพลาดในการประมวลผลเสียง: {e}"}, status=500)

    def _handle_voice_transcribe(self, payload: Dict[str, Any]):
        """Transcribes audio payload only without executing chat turn."""
        audio_b64 = payload.get("audio_base64") or payload.get("audio") or ""
        if not audio_b64:
            self._send_json({"error": "audio_base64 is required"}, status=400)
            return
        if not engine:
            self._send_json({"error": "VoiceEngine not initialized"}, status=500)
            return
        try:
            if "," in audio_b64:
                audio_b64 = audio_b64.split(",", 1)[1]
            audio_bytes = base64.b64decode(audio_b64)
            t_start = time.time()
            transcript = engine.transcribe_audio(audio_bytes)
            stt_duration = round(time.time() - t_start, 2)
            self._send_json({
                "success": True,
                "transcript": transcript,
                "audio_size_bytes": len(audio_bytes),
                "duration_seconds": stt_duration
            })
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _handle_save_config(self, payload: Dict[str, Any]):
        for key in ["voice", "speed", "pitch", "model", "temperature", "auto_speak", "glass_blur", "glass_opacity"]:
            if key in payload:
                RUNTIME_CONFIG[key] = payload[key]
        save_stored_config(RUNTIME_CONFIG)
        self._send_json({"success": True, "config": RUNTIME_CONFIG})

    def _handle_tts(self, payload: Dict[str, Any]):
        text = payload.get("text", "").strip()
        voice = payload.get("voice") or RUNTIME_CONFIG.get("voice", "th-TH-PremwadeeNeural")
        speed = payload.get("speed") or RUNTIME_CONFIG.get("speed", "+0%")
        pitch = payload.get("pitch") or RUNTIME_CONFIG.get("pitch", "+0Hz")
        if not text:
            self._send_json({"error": "text is required"}, status=400)
            return
        try:
            f_path, chunks, dur = synthesize_speech_multiround(text, voice=voice, speed=speed, pitch=pitch)
            self._send_json({
                "success": True,
                "audio_url": f"/audio/{f_path.name}",
                "duration_seconds": round(dur, 2)
            })
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _serve_audio(self, is_head: bool = False):
        raw_target = self.path.split("?")[0]
        if ".." in raw_target or "\x00" in raw_target or "\\" in raw_target:
            self.send_error(400, "Bad Request: Directory traversal attempt detected")
            return
        fname = os.path.basename(raw_target)
        candidate_paths = [
            AUDIO_CACHE_DIR / fname,
            Path(tempfile.gettempdir()) / "hermes_voice" / fname,
            Path("C:/Users/Administrator/AppData/Local/Temp/hermes_voice") / fname,
            Path("C:/Users/Administrator/AppData/Local/Temp/2/hermes_voice") / fname,
            Path("C:/Users/Administrator/AppData/Local/Temp/1/hermes_voice") / fname,
        ]
        if engine and hasattr(engine, "_temp_dir"):
            candidate_paths.append(engine._temp_dir / fname)

        audio_path = None
        for cp in candidate_paths:
            if cp.exists():
                audio_path = cp
                break

        if not audio_path:
            self.send_error(404, "Audio file not found")
            return

        file_size = audio_path.stat().st_size
        range_header = self.headers.get("Range")

        if range_header and range_header.startswith("bytes="):
            try:
                ranges = range_header.replace("bytes=", "").split("-")
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
                if start > end or start >= file_size or start < 0:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    return
                end = min(end, file_size - 1)
                content_length = end - start + 1

                self.send_response(206)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(content_length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                if not is_head:
                    with open(audio_path, "rb") as f:
                        f.seek(start)
                        self.wfile.write(f.read(content_length))
                return
            except Exception:
                pass

        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        if not is_head:
            self.wfile.write(audio_path.read_bytes())

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        except Exception:
            pass

def synthesize_speech_multiround(
    text: str,
    voice: str = "th-TH-PremwadeeNeural",
    speed: str = "+0%",
    pitch: str = "+0Hz"
) -> Tuple[Path, List[str], float]:
    """Parallel multi-round Edge-TTS synthesis for long text with clean seamless audio merge."""
    clean_text = maymint_brain.clean_text_for_speech_full(text) if maymint_brain else text
    t0 = time.time()
    temp_dir = Path(tempfile.gettempdir()) / "hermes_voice"
    temp_dir.mkdir(parents=True, exist_ok=True)

    if engine:
        f = engine.synthesize_speech(clean_text, voice=voice, speed=speed, pitch=pitch)
        return f, [clean_text], time.time() - t0

    # Fallback to direct edge_tts
    import edge_tts
    comm = edge_tts.Communicate(clean_text, voice, rate=speed, pitch=pitch)
    out_file = AUDIO_CACHE_DIR / f"speech_{secrets.token_hex(4)}.mp3"
    import asyncio
    asyncio.run(comm.save(str(out_file)))
    return out_file, [clean_text], time.time() - t0

def run_server():
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("0.0.0.0", PORT), VoiceRequestHandler)
    logger.info("🌸 Maymint Liquid Glass Dashboard running at http://127.0.0.1:%d/ (PIN Secured)", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped.")
        server.server_close()

if __name__ == "__main__":
    run_server()
