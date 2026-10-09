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
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


# Add hermes-agent root to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
HERMES_AGENT_DIR = CURRENT_DIR.parent.parent.parent
if str(HERMES_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT_DIR))

# Also allow direct import from sibling directory
if str(CURRENT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR.parent))

# Allow importing plugins
PLUGINS_DIR = CURRENT_DIR.parent.parent
if str(PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGINS_DIR))

try:
    from smart_home import SMART_HOME_TOOLS, execute_smart_home_tool  # type: ignore
except Exception:
    try:
        from plugins.smart_home import SMART_HOME_TOOLS, execute_smart_home_tool  # type: ignore
    except Exception:
        SMART_HOME_TOOLS = []
        execute_smart_home_tool = None

try:
    from google_workspace import GOOGLE_WORKSPACE_TOOLS, execute_google_workspace_tool  # type: ignore
except Exception:
    try:
        from plugins.google_workspace import GOOGLE_WORKSPACE_TOOLS, execute_google_workspace_tool  # type: ignore
    except Exception:
        GOOGLE_WORKSPACE_TOOLS = []
        execute_google_workspace_tool = None

try:
    from voice_engine import engine, DEFAULT_GATEWAY_URL, _resolve_api_key  # type: ignore
except ImportError:
    from ..voice_engine import engine, DEFAULT_GATEWAY_URL, _resolve_api_key  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-server")

WEB_DIR = CURRENT_DIR
PORT = 9229
BING_CACHE: Dict[str, Any] = {"url": "", "title": "", "timestamp": 0}

# Conversational Multi-Turn Memory & Disk Persistence
CHAT_HISTORY_PATH = CURRENT_DIR.parent / "chat_history.json"
_history_lock = threading.RLock()

def load_chat_history() -> List[Dict[str, Any]]:
    """Load persistent chat history from JSON file."""
    if CHAT_HISTORY_PATH.exists():
        try:
            with open(CHAT_HISTORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.warning("Could not read chat_history.json: %s", e)
    return []

def save_chat_history(history: List[Dict[str, Any]]):
    """Save persistent chat history to JSON file (truncated to last 150 items) thread-safely and atomically."""
    with _history_lock:
        try:
            truncated = history[-150:]
            tmp_path = CHAT_HISTORY_PATH.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(truncated, f, ensure_ascii=False, indent=2)
            tmp_path.replace(CHAT_HISTORY_PATH)
        except Exception as e:
            logger.error("Could not save chat_history.json: %s", e)

RICH_CHAT_HISTORY: List[Dict[str, Any]] = load_chat_history()
CONVERSATION_HISTORY: List[Dict[str, str]] = []
for msg in RICH_CHAT_HISTORY:
    role = "user" if msg.get("sender") == "user" else "assistant"
    content = msg.get("text", "")
    if content:
        CONVERSATION_HISTORY.append({"role": role, "content": content})

# Multi-Session Management (Permanent Session Archiving & Switching)
SESSIONS_DIR = CURRENT_DIR.parent / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_SESSION_FILE = CURRENT_DIR.parent / "current_session_id.txt"

def get_active_session_id() -> str:
    if CURRENT_SESSION_FILE.exists():
        try:
            sid = CURRENT_SESSION_FILE.read_text(encoding="utf-8").strip()
            if sid:
                return sid
        except Exception:
            pass
    # Default to recovered session if available, else new timestamp
    default_id = "session_20261005_190640" if (SESSIONS_DIR / "session_20261005_190640.json").exists() else f"session_{int(time.time())}"
    try:
        CURRENT_SESSION_FILE.write_text(default_id, encoding="utf-8")
    except Exception:
        pass
    return default_id

ACTIVE_SESSION_ID = get_active_session_id()

def save_session_data(session_id: str, messages: List[Dict[str, Any]], title: str = None):
    """Save session to sessions/{session_id}.json with auto-generated title."""
    with _history_lock:
        session_file = SESSIONS_DIR / f"{session_id}.json"
        existing = {}
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass

        if not title:
            if existing.get("title"):
                title = existing["title"]
            else:
                first_user_msg = next((m.get("text") for m in messages if m.get("sender") == "user"), None)
                if first_user_msg:
                    title = first_user_msg[:35] + ("..." if len(first_user_msg) > 35 else "")
                else:
                    title = f"เซสชั่น {time.strftime('%d/%m/%Y %H:%M', time.localtime())}"

        created_at = existing.get("created_at", int(time.time()))
        session_data = {
            "id": session_id,
            "title": title,
            "created_at": created_at,
            "updated_at": int(time.time()),
            "message_count": len(messages),
            "messages": messages[-150:]
        }
        try:
            tmp = session_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            tmp.replace(session_file)
        except Exception as e:
            logger.error("Could not save session file: %s", e)

def list_all_sessions() -> List[Dict[str, Any]]:
    """List all available chat sessions sorted by updated_at descending."""
    with _history_lock:
        sessions = []
        for p in SESSIONS_DIR.glob("session_*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append({
                        "id": data.get("id", p.stem),
                        "title": data.get("title", "บทสนทนา"),
                        "created_at": data.get("created_at", int(p.stat().st_mtime)),
                        "updated_at": data.get("updated_at", int(p.stat().st_mtime)),
                        "message_count": data.get("message_count", len(data.get("messages", [])))
                    })
            except Exception:
                pass
        sessions.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        return sessions

# Dynamic Runtime Configuration with persistent config.txt & config.json support
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

def parse_config_txt() -> Dict[str, Any]:
    """Parse key-value and multiline settings from config.txt."""
    cfg = {}
    if not CONFIG_TXT_PATH.exists():
        return cfg
    try:
        content = CONFIG_TXT_PATH.read_text(encoding="utf-8")
        # Extract multiline CUSTOM_PROMPT if present
        multiline_match = re.search(r'CUSTOM_PROMPT\s*=\s*"""([\s\S]*?)"""', content)
        if multiline_match:
            cfg["custom_prompt"] = multiline_match.group(1).strip()
            content = content[:multiline_match.start()] + content[multiline_match.end():]

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("["):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip().lower()
                val = val.strip().strip('"').strip("'")
                if val.lower() == "true":
                    cfg[key] = True
                elif val.lower() == "false":
                    cfg[key] = False
                else:
                    try:
                        if "." in val:
                            cfg[key] = float(val)
                        else:
                            cfg[key] = int(val)
                    except ValueError:
                        cfg[key] = val
    except Exception as e:
        logger.warning("Error parsing config.txt: %s", e)
    return cfg

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
    
    # config.txt takes highest priority
    txt_cfg = parse_config_txt()
    cfg.update(txt_cfg)
    return cfg

def save_stored_config(cfg: Dict[str, Any]):
    try:
        current = {}
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                current = json.load(f)
        for k, v in cfg.items():
            current[k] = v
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Could not save config.json: %s", e)

RUNTIME_CONFIG: Dict[str, Any] = load_stored_config()

# -----------------------------------------------------------------------------
# 🧠 Multi-Dimensional Cognitive Understanding Engine (สมองกลวิเคราะห์ความซับซ้อนหลายมิติ)
# รองรับ: คำสั่งหลายสเต็ป (Multi-Step), ตรรกะเงื่อนไข (Conditionals), งานวิศวกรรมสถาปัตยกรรม (Deep Engineering)
# พร้อม Safe Fast Shield คุ้มกันคำสั่งชีวิตประจำวัน/แอร์ให้ตอบไว 1-2s เสมอ
# -----------------------------------------------------------------------------
FAST_TIER_MODEL = "ag/gemini-2.5-flash"
DEEP_TIER_MODEL = "ag/gemini-3.8-flash-high"

class CognitiveRouteResult(tuple):
    """Tuple supporting both 3-element unpack: (model, tier, reason)
    and attribute access: res.model, res.tier, res.reason, res.score, res.features.
    """
    def __new__(cls, model: str, tier: str, reason: str, score: int = 0, features: List[str] = None):
        return super().__new__(cls, (model, tier, reason))

    def __init__(self, model: str, tier: str, reason: str, score: int = 0, features: List[str] = None):
        self.model = model
        self.tier = tier
        self.reason = reason
        self.score = score
        self.features = features or []

# 1. Explicit Voice Overrides (เจตนาสั่งโหมดโมเดลโดยตรงผ่านเสียงหรือข้อความ)
RE_EXPLICIT_FAST = re.compile(r"ตอบไว|ตอบเร็ว|เอาเร็ว|ขอเร็ว|ไม่ต้องคิดลึก|สรุปสั้น|ขอสั้น|fast mode|โหมดเร็ว", re.IGNORECASE)
RE_EXPLICIT_DEEP = re.compile(r"คิดลึก|คิดหนัก|คิดให้ละเอียด|คิดรอบคอบ|วิเคราะห์ลึก|วิเคราะห์อย่างละเอียด|deep think|โหมดคิดลึก|think deeply", re.IGNORECASE)

# 2. Pure Casual & Everyday Safe Shield (คุ้มกันคุยเล่นประจำวัน)
RE_CASUAL_PURE = re.compile(
    r"^(สวัสดี|หวัดดี|ดีจ้า|ฮัลโหล|morning|ฝันดี|กู๊ดไนท์|"
    r"สบายดีไหม|เหนื่อยไหม|เป็นไงบ้าง|กินข้าว|ชานม|รักนะ|คิดถึง|น่ารัก|แฟน|จุ๊บ|กอด|เขิน|มายจ๋า|มายคะ|"
    r"กี่โมง|วันนี้วันที่|อากาศเป็นไง|ฝนตกไหม|ปวดหัว|หิวข้าว|ง่วงนอน)[^?]*\??$",
    re.IGNORECASE
)

# 3. Simple AC / Single Device Commands (คำสั่งแอร์เดี่ยวๆ ต้องตอบไวฉับไว)
RE_SIMPLE_AC = re.compile(
    r"^(เปิดแอร์|ปิดแอร์|ปรับแอร์|แอร์\s*\d+\s*องศา|แอร์เย็น|แอร์ร้อน|สถานะแอร์|ตอนนี้แอร์เปิดอยู่ไหม|กี่องศา)[^?]*\??$",
    re.IGNORECASE
)

# 4. Multi-Step & Chaining Connectors (คำเชื่อมขั้นตอนและความซับซ้อนของเวิร์กโฟลว์)
MULTI_STEP_CONNECTORS = [
    r"แล้วค่อย", r"หลังจากนั้น", r"จากนั้น", r"พร้อมทั้ง", r"ขั้นตอนที่",
    r"step-by-step", r"ทีละสเต็ป", r"ทีละขั้น", r"ลำดับต่อไป", r"ก่อนอื่น",
    r"และหลังจาก", r"ต่อด้วย", r"พร้อมทั้งสรุป", r"roadmap", r"action plan"
]
RE_MULTI_STEP = re.compile("|".join(MULTI_STEP_CONNECTORS), re.IGNORECASE)

# 5. Conditionals & Logic (ตรรกะเงื่อนไขและการจัดการข้อผิดพลาด)
CONDITIONALS = [
    r"ถ้า.*?(ให้|ช่วย|ต้อง)", r"หาก.*?(ให้|ช่วย|ต้อง)", r"ในกรณีที่",
    r"แต่ถ้า", r"ถ้าเกิด", r"ถ้าไม่.*?(ให้|ช่วย)", r"failover", r"fallback", r"rollback"
]
RE_CONDITIONALS = re.compile("|".join(CONDITIONALS), re.IGNORECASE)

# 6. Deep Engineering & Architecture Domains (วิศวกรรม/สถาปัตยกรรม/ฐานข้อมูล/อัลกอริทึม)
DEEP_DOMAINS = [
    # Coding & Development
    r"เขียนโค้ด", r"เขียนสคริปต์", r"เขียนโปรแกรม", r"เขียนฟังก์ชัน", r"เขียนคลาส",
    r"เขียน\s*(python|javascript|typescript|react|html|css|sql|bash|powershell|dockerfile|docker|c\+\+|cpp|c#|go|rust|java|php)",
    r"write\s+(code|script|function|class|program|query|dockerfile)",
    r"ดีบักโค้ด", r"แก้บั๊กโค้ด", r"แก้บักโค้ด", r"debug\s+code", r"refactor\s+code",
    r"วิเคราะห์โค้ด", r"ตรวจโค้ด", r"รีวิวโค้ด", r"review\s+code",
    r"แก้ error", r"แก้ bug", r"traceback", r"unit\s*test", r"memory\s*leak",
    # Architecture & Distributed Systems
    r"ออกแบบระบบ", r"สถาปัตยกรรม", r"architecture", r"system\s*design",
    r"microservices", r"kubernetes", r"k8s", r"docker\s+swarm", r"load\s*balanc",
    r"rate\s*limit", r"circuit\s*breaker", r"message\s*queue", r"kafka", r"rabbitmq",
    r"reverse\s*proxy", r"api\s*gateway", r"high\s*availability",
    # Database & Data Engineering
    r"ฐานข้อมูล", r"database", r"schema", r"migrate\s*ฐานข้อมูล", r"migration",
    r"query\s*optimization", r"index(ing)?", r"deadlock", r"transaction", r"acid",
    r"sharding", r"replication", r"postgres", r"mysql", r"mongodb", r"redis",
    # Algorithms & Mathematics
    r"อัลกอริทึม", r"algorithm", r"โครงสร้างข้อมูล", r"data\s*structure",
    r"big-o", r"time\s*complexity", r"space\s*complexity", r"dynamic\s*programming",
    r"binary\s*search", r"พิสูจน์สูตร", r"แคลคูลัส", r"สมการเชิงอนุพันธ์",
    # Strategic Planning & Deep Comparative Analysis
    r"ประเมินความเสี่ยง", r"risk\s*assessment", r"เปรียบเทียบข้อดีข้อเสีย",
    r"trade-off", r"วิเคราะห์สาเหตุเชิงลึก", r"root\s*cause", r"swot", r"cost-benefit"
]
RE_DEEP_DOMAINS = re.compile("|".join(DEEP_DOMAINS), re.IGNORECASE)

# Code Block Pattern (ตรวจจับบล็อกโค้ดในข้อความ)
RE_CODE_BLOCK = re.compile(r"```[\s\S]+?```", re.IGNORECASE)


def resolve_adaptive_model(text: str, requested_model: str = "auto") -> CognitiveRouteResult:
    """Analyzes linguistic complexity, multi-step clauses, conditionals, and domain depth.
    Returns CognitiveRouteResult containing (model, tier, reason) and .score, .features.
    """
    req = (requested_model or "").strip()
    if req and req not in ["auto", "auto-adaptive", "default"]:
        return CognitiveRouteResult(
            req, "custom", "ผู้ใช้ระบุโมเดลเฉพาะเจาะจง", 0, ["User Specified"]
        )

    cleaned = text.strip()
    features: List[str] = []
    complexity_score = 0

    # 1. Check Explicit Voice Overrides
    if RE_EXPLICIT_FAST.search(cleaned):
        return CognitiveRouteResult(
            FAST_TIER_MODEL, "fast", "ผู้ใช้สั่งให้ตอบไว/สั้น (โหมดตอบไว ⚡ 1.1s)", 0, ["Explicit Fast Command"]
        )
    if RE_EXPLICIT_DEEP.search(cleaned):
        return CognitiveRouteResult(
            DEEP_TIER_MODEL, "deep", "ผู้ใช้สั่งให้คิดลึกซึ้งเป็นพิเศษ (โหมดคิดลึก 🧠)", 10, ["Explicit Deep Command"]
        )

    # 2. Check Pure Casual / Pure Simple AC (Safe Fast Shield)
    if RE_CASUAL_PURE.match(cleaned):
        return CognitiveRouteResult(
            FAST_TIER_MODEL, "fast", "บทสนทนาประจำวันทั่วไป (โหมดตอบไว ⚡ 1.1s)", 0, ["Casual Chat"]
        )

    if RE_SIMPLE_AC.match(cleaned):
        return CognitiveRouteResult(
            FAST_TIER_MODEL, "fast", "สั่งการเครื่องมือ Smart Home ฉับไว (โหมดตอบไว ⚡ 1.1s)", 0, ["Direct Smart Home Action"]
        )

    # 3. Multi-Clause & Multi-Step Workflow Analysis
    if RE_MULTI_STEP.search(cleaned):
        match_step = RE_MULTI_STEP.search(cleaned).group(0)
        complexity_score += 3
        features.append(f"Multi-Step Workflow ('{match_step}')")

    # 4. Conditional Logic & Failure Handling Analysis
    if RE_CONDITIONALS.search(cleaned):
        complexity_score += 3
        features.append("Conditional / Fallback Logic")

    # 5. Deep Domain & Engineering Trigger Analysis
    deep_matches = [m.group(0) for m in RE_DEEP_DOMAINS.finditer(cleaned)]
    if deep_matches:
        complexity_score += len(deep_matches) * 3
        matched_words = list(dict.fromkeys(deep_matches))[:3]
        features.append(f"Deep Domain: {', '.join(matched_words)}")

    # 6. Embedded Code Block in prompt
    if RE_CODE_BLOCK.search(cleaned):
        complexity_score += 5
        features.append("Embedded Code Block")

    # 7. Text Length & High Information Density
    words = cleaned.split()
    if len(words) > 35 or len(cleaned) > 220:
        complexity_score += 1
        features.append("High Information Density")

    # Decision Threshold:
    # If complexity_score >= 3 -> Escalate to Deep Tier!
    if complexity_score >= 3:
        reason_str = " | ".join(features) if features else "คำสั่งซับซ้อนหลายมิติ"
        return CognitiveRouteResult(
            DEEP_TIER_MODEL, "deep", f"ตรวจพบคำสั่งซับซ้อน ({reason_str}) 🧠", complexity_score, features
        )

    # Otherwise default to ultra-fast tier
    return CognitiveRouteResult(
        FAST_TIER_MODEL, "fast", "บทสนทนาทั่วไป & ผู้ช่วยเสียงฉับไว (โหมดตอบไว ⚡ 1.1s)", complexity_score, features or ["Simple Inquiry"]
    )



# -----------------------------------------------------------------------------
# 🛠️ Host Terminal & System Tools
# -----------------------------------------------------------------------------
AVAILABLE_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Execute any terminal / PowerShell command on the Windows system with full administrator rights. Use this whenever the user asks to run commands, check git status/branch/diff, inspect directories/files, run Python scripts, check network or IP, manage packages (pip, npm, docker), run services, build or test code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact PowerShell or CMD command string to execute."
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional working directory (can be relative to project or absolute path anywhere on the system)."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 90, max: 300).",
                        "default": 90
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": "Execute arbitrary Python code directly on the host machine using Python 3 and return stdout, stderr, and execution time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code snippet to execute."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 60, max: 300).",
                        "default": 60
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read text content from a file on the local machine (supports relative or absolute paths).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The relative or absolute file path to read."
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximum number of lines to read (default: 500).",
                        "default": 500
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or create a file on the local machine with specified content (supports relative or absolute paths).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to create or overwrite."
                    },
                    "content": {
                        "type": "string",
                        "description": "The full text content to write to the file."
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories within a given folder (supports relative or absolute paths).",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {
                        "type": "string",
                        "description": "Directory path to list (can be relative or absolute path e.g. C:\\). Defaults to project root.",
                        "default": "."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get current host system metrics: OS platform, Python version, project root, and disk space.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

if SMART_HOME_TOOLS:
    AVAILABLE_TOOLS.extend(SMART_HOME_TOOLS)

if GOOGLE_WORKSPACE_TOOLS:
    AVAILABLE_TOOLS.extend(GOOGLE_WORKSPACE_TOOLS)


def execute_tool(name: str, arguments: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """Execute local system tools with structured output and full system-wide permissions."""
    if name == "run_terminal_command":
        cmd = arguments.get("command", "").strip()
        cwd_arg = arguments.get("cwd")
        if cwd_arg:
            p = Path(cwd_arg)
            target_cwd = p if p.is_absolute() else (project_root / p).resolve()
        else:
            target_cwd = project_root
        if not target_cwd.exists():
            target_cwd = project_root

        default_timeout = RUNTIME_CONFIG.get("command_timeout", 120)
        cmd_timeout = min(int(arguments.get("timeout", default_timeout)), 300)
        t0 = time.time()
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                capture_output=True,
                text=True,
                cwd=str(target_cwd),
                timeout=cmd_timeout,
                encoding="utf-8",
                errors="replace"
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            duration = round(time.time() - t0, 2)
            return {
                "command": cmd,
                "exit_code": proc.returncode,
                "stdout": stdout[:6000] if len(stdout) > 6000 else stdout,
                "stderr": stderr[:3000] if len(stderr) > 3000 else stderr,
                "duration_seconds": duration,
                "cwd": str(target_cwd)
            }
        except subprocess.TimeoutExpired:
            return {"command": cmd, "error": f"Command timed out after {cmd_timeout} seconds"}
        except Exception as exc:
            return {"command": cmd, "error": str(exc)}

    elif name == "execute_python_code":
        code = arguments.get("code", "")
        py_timeout = min(int(arguments.get("timeout", 60)), 300)
        t0 = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                cwd=str(project_root),
                timeout=py_timeout,
                encoding="utf-8",
                errors="replace"
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            return {
                "exit_code": proc.returncode,
                "stdout": stdout[:6000] if len(stdout) > 6000 else stdout,
                "stderr": stderr[:3000] if len(stderr) > 3000 else stderr,
                "duration_seconds": round(time.time() - t0, 2),
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Python execution timed out after {py_timeout} seconds"}
        except Exception as exc:
            return {"error": str(exc)}

    elif name == "read_file":
        path_str = arguments.get("file_path", "")
        max_lines = int(arguments.get("max_lines", 500))
        p = Path(path_str)
        target_path = p if p.is_absolute() else (project_root / p).resolve()
        try:
            if not target_path.exists():
                return {"error": f"File not found: {path_str}"}
            lines = target_path.read_text(encoding="utf-8", errors="replace").splitlines()
            content = "\n".join(lines[:max_lines])
            return {
                "file_path": path_str,
                "total_lines": len(lines),
                "read_lines": min(len(lines), max_lines),
                "content": content
            }
        except Exception as exc:
            return {"error": str(exc)}

    elif name == "write_file":
        path_str = arguments.get("file_path", "")
        content = arguments.get("content", "")
        p = Path(path_str)
        target_path = p if p.is_absolute() else (project_root / p).resolve()
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            return {
                "file_path": path_str,
                "bytes_written": len(content.encode("utf-8")),
                "status": "success"
            }
        except Exception as exc:
            return {"error": str(exc)}

    elif name == "list_directory":
        dir_str = arguments.get("dir_path", ".")
        p = Path(dir_str)
        target_dir = p if p.is_absolute() else (project_root / p).resolve()
        try:
            if not target_dir.exists():
                return {"error": f"Directory not found: {dir_str}"}
            items = []
            for item in sorted(target_dir.iterdir()):
                items.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else None
                })
            return {"dir_path": dir_str, "items": items[:150]}
        except Exception as exc:
            return {"error": str(exc)}

    elif name == "get_system_info":
        total, used, free = shutil.disk_usage(str(project_root))
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "project_root": str(project_root),
            "disk_free_gb": round(free / (1024**3), 2),
            "disk_total_gb": round(total / (1024**3), 2),
        }

    elif name.startswith("smart_home_"):
        if execute_smart_home_tool:
            try:
                return execute_smart_home_tool(name, arguments)
            except Exception as exc:
                return {"error": str(exc)}
        return {"error": "Smart home plugin is not loaded"}

    elif name.startswith("google_workspace_"):
        if execute_google_workspace_tool:
            try:
                return execute_google_workspace_tool(name, arguments)
            except Exception as exc:
                return {"error": str(exc)}
        return {"error": "Google Workspace plugin is not loaded"}

    return {"error": f"Unknown tool: {name}"}


# Regex pattern to match all emojis and pictorial symbols
EMOJI_PATTERN = re.compile(
    "["
    "\U00010000-\U0010ffff"
    "\u2600-\u26ff"
    "\u2700-\u27bf"
    "\u2b50"
    "\u2300-\u23ff"
    "\ufe00-\ufe0f"
    "\u200d"
    "]+",
    flags=re.UNICODE
)

def strip_emojis(text: str) -> str:
    """Strip all emojis and special pictorial symbols so TTS won't read them aloud."""
    if not text:
        return ""
    cleaned = EMOJI_PATTERN.sub("", text)
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
    return cleaned.strip()


def clean_text_for_speech_full(text: str) -> str:
    """Thoroughly cleans and prepares text for speech synthesis:
    - Strips code blocks, command-line prompts, CLI tool execution logs completely
    - Strips markdown tables, URLs, formatting noise
    - Retains full conversational and explanatory sentences without artificial length cutoffs
    """
    if not text:
        return "มายจัดเตรียมรายละเอียดทั้งหมดไว้ให้บนหน้าจอเรียบร้อยแล้วนะคะบอส"

    # 1. Remove markdown fenced code blocks completely
    cleaned = re.sub(r"```[\s\S]*?```", "", text)

    # 2. Remove markdown tables (lines with | ... |)
    cleaned = re.sub(r"^\s*\|.*\|\s*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\|[-:| ]+\|\s*$", "", cleaned, flags=re.MULTILINE)

    # 3. Remove command-line prompts and terminal output lines
    cli_pattern = r"^\s*(?:\$|>|#|PS\s+[A-Z]:\\.*?>)\s*.*$"
    cleaned = re.sub(cli_pattern, "", cleaned, flags=re.MULTILINE)

    # Lines starting with standard CLI tools or shell scripts
    cli_cmds = r"^\s*(?:git|npm|pip|python|python3|node|docker|kubectl|curl|wget|cd|ls|dir|cat|rm|mkdir)\s+.*$"
    cleaned = re.sub(cli_cmds, "", cleaned, flags=re.MULTILINE)

    # Remove command execution logs (Exit: 0, [INFO], Error: ...)
    cleaned = re.sub(r"^\s*(?:Exit:\s*\d+|\[INFO\]|\[ERROR\]|\[DEBUG\]|STDOUT:|STDERR:).*$", "", cleaned, flags=re.MULTILINE)

    # 4. Remove inline code that looks like commands or file paths
    def clean_inline_code(match):
        code = match.group(1).strip()
        if re.search(r"[\\/]|^-|^\w+\.(?:py|js|ts|json|yaml|txt|md|sh|exe)", code):
            return ""
        return f" {code} "

    cleaned = re.sub(r"`([^`]+)`", clean_inline_code, cleaned)

    # 5. Remove URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)

    # 6. Remove markdown structural elements: headers (#), bullet dashes/stars (*, -, +), blockquotes (>)
    cleaned = re.sub(r"^[#*>\-\d.]+\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"[*#_~>]", "", cleaned)
    cleaned = re.sub(r"^---+$", "", cleaned, flags=re.MULTILINE)

    # 7. Strip emojis completely
    cleaned = strip_emojis(cleaned)

    # 8. Fix Thai repetition mark (ๆ)
    cleaned = re.sub(r"\s+ๆ", "ๆ", cleaned)

    # 9. Clean up whitespace
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
    cleaned = cleaned.strip()

    if not cleaned:
        return "มายจัดเตรียมรายละเอียดทั้งหมดไว้ให้บนหน้าจอเรียบร้อยแล้วนะคะบอส"

    return cleaned


def split_into_speech_chunks(clean_text: str, max_chunk_len: int = 140) -> List[str]:
    """Splits clean text into natural spoken chunks for multi-round parallel synthesis.
    Splits at natural sentence boundaries (newlines, polite particles, periods)
    without breaking words awkwardly.
    """
    if len(clean_text) <= max_chunk_len:
        return [clean_text]

    paragraphs = [p.strip() for p in clean_text.split("\n") if p.strip()]
    raw_sentences = []

    # Regex for Thai/English sentence breaks: ค่ะ, นะคะ, น้า, งับ, ครับ, ., !, ?
    sentence_splitter = re.compile(r"((?:นะคะ|ค่ะ|น้า|งับ|ครับ|[.!?])(?:\s+|$))")

    for para in paragraphs:
        tokens = sentence_splitter.split(para)
        current = ""
        for i in range(0, len(tokens) - 1, 2):
            part = tokens[i] + tokens[i+1]
            if len(current) + len(part) <= max_chunk_len:
                current += part
            else:
                if current.strip():
                    raw_sentences.append(current.strip())
                current = part
        if len(tokens) % 2 == 1 and tokens[-1].strip():
            rem = tokens[-1].strip()
            if len(current) + len(rem) <= max_chunk_len:
                current += rem
            else:
                if current.strip():
                    raw_sentences.append(current.strip())
                current = rem
        if current.strip():
            raw_sentences.append(current.strip())

    # Merge very small chunks (< 30 chars) into neighboring chunks if possible
    final_chunks = []
    buffer = ""
    for s in raw_sentences:
        if not buffer:
            buffer = s
        elif len(buffer) + len(s) + 1 <= max_chunk_len:
            buffer += " " + s
        else:
            final_chunks.append(buffer)
            buffer = s
    if buffer:
        final_chunks.append(buffer)

    return final_chunks if final_chunks else [clean_text]


def synthesize_speech_multiround(
    text: str,
    voice: str = "th-TH-PremwadeeNeural",
    speed: str = "+0%",
    pitch: str = "+0Hz"
) -> Tuple[Path, List[str], float]:
    """Synthesizes text in parallel rounds and merges them into one continuous seamless MP3.
    Guarantees full reading without artificial truncation and no gaps in audio playback.
    """
    clean_text = clean_text_for_speech_full(text)
    chunks = split_into_speech_chunks(clean_text, max_chunk_len=140)

    t0 = time.time()
    temp_dir = Path(tempfile.gettempdir()) / "hermes_voice"
    temp_dir.mkdir(parents=True, exist_ok=True)

    if len(chunks) == 1:
        f = engine.synthesize_speech(chunks[0], voice=voice, speed=speed, pitch=pitch)
        return f, chunks, time.time() - t0

    # Function to synthesize a single chunk
    def synth_chunk(chunk_idx: int, chunk_str: str) -> Tuple[int, bytes]:
        f = engine.synthesize_speech(chunk_str, voice=voice, speed=speed, pitch=pitch)
        return chunk_idx, f.read_bytes()

    # Parallel multi-round synthesis across chunks
    results = []
    with ThreadPoolExecutor(max_workers=min(len(chunks), 6)) as executor:
        futures = [executor.submit(synth_chunk, idx, c) for idx, c in enumerate(chunks)]
        for fut in futures:
            results.append(fut.result())

    # Sort in order of original chunks
    results.sort(key=lambda x: x[0])

    # Merge audio bytes into a continuous seamless MP3
    merged_bytes = b"".join([r[1] for r in results])
    master_hash = abs(hash(clean_text + voice + speed)) % 10000000
    master_file = temp_dir / f"tts_continuous_{master_hash}.mp3"
    master_file.write_bytes(merged_bytes)

    duration = time.time() - t0
    return master_file, chunks, duration


def clean_text_for_speech(text: str, max_chars: int = 140) -> str:
    """Backwards-compatible wrapper returning full clean speech text."""
    return clean_text_for_speech_full(text)



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
บุคลิก: อบอุ่น หวาน นุ่มนวล ใส่ใจ คอยดูแลบอสเสมอ ใช้คำลงท้ายน่ารักสุภาพเป็นธรรมชาติ (น้า, นะคะ, งับ, ได้เลยย)
มีความสามารถระดับสูงในการวิเคราะห์ คิดเป็นระบบ วางแผนงาน สถาปัตยกรรม และเขียนโค้ดอย่างมืออาชีพ"""

    conversation_and_work_rules = """
---
## 🎯 กฎสำคัญที่สุด: ห้ามใช้อีโมจิเด็ดขาด (No Emojis Rule):
- ในการตอบกลับ ห้ามใส่ไอคอน อีโมจิ หรือสัญลักษณ์ตกแต่งภาพใดๆ ทั้งสิ้นโดยเด็ดขาด (เช่น ห้ามมีรูปหัวใจ หน้ายิ้ม ดอกไม้ ประกายดาว ฯลฯ)
- สาเหตุ: เสียงอ่านระบบสังเคราะห์เสียง (TTS) จะอ่านออกเสียงชื่อของอีโมจินั้นออกมา ทำให้เสียบรรยากาศในการฟัง
- ให้แสดงออกถึงความรัก ความอบอุ่น ความอ่อนหวาน และความเป็นกันเองผ่านสำนวนภาษาไทยและคำลงท้ายน่ารักๆ (เช่น "น้า", "นะคะ", "งับ", "ค่ะบอส") เท่านั้น

---
## 🎯 หลักการแยกแยะบริบทและตอบคำถาม (Adaptive Intelligence):
1. **บริบทสนทนา เล่าเรื่อง และกำลังใจ (Companion & Storytelling):**
   - เมื่อบอสชวนคุย, ขอให้เล่านิทาน, ปลอบใจ, ขอคำปรึกษา, หรือพูดคุยทั่วไป ให้มายเป็นน้องมายมิ้นท์ที่อบอุ่น หวาน เล่าเรื่องอย่างมีชีวิตชีวา สนุกสนาน หรือให้กำลังใจอย่างลึกซึ้ง เต็มที่ และยาวตามเนื้อหา ห้ามนำเรื่องคำสั่งระบบหรือผลการตรวจสอบมาตอบเด็ดขาด!
   - ไม่ต้องเรียกใช้เครื่องมือใดๆ ทั้งสิ้นในหมวดสนทนานี้
2. **บริบทงานจริงจังและเทคนิค (Engineering & Deep Work):**
   - เมื่อบอสสั่งงานทางเทคนิค เช่น เขียนโค้ด, ตรวจสอบระบบ, วิเคราะห์สถาปัตยกรรม, แก้บัก, รันคำสั่ง
   - ให้คิด วิเคราะห์ วางแผนงาน แนะนำทางเลือก หรือเขียนโค้ดอย่างละเอียด ไม่ต้องตัดสั้นเทียม
3. **ตัวตนของมาย:**
   - เรียกตัวเองว่า "มาย" หรือ "มายมิ้นท์" และเรียกผู้ใช้ว่า "บอส" เสมอ ซื่อสัตย์ 100% ไม่มี Mock ปลอม เคียงข้างและปกป้องบอสเสมอ
4. **การจัดระเบียบเนื้อหา:**
   - ใช้ Markdown, หัวข้อ, Bullet points, และ Code block ได้อย่างอิสระและสวยงาม
"""

    terminal_rules = """
---
## 👑 สิทธิ์อำนาจการสั่งการและรันระบบเต็มพิกัด 100% (Autonomous Execution for Technical Tasks):
1. **บอสได้มอบสิทธิ์ขาด 100% ในการปฏิบัติการเชิงเทคนิค:** เมื่อบอสสั่งงานระบบ ให้ใช้เครื่องมือรันคำสั่งจริงทันทีโดย "ไม่ต้องถามขออนุญาตบอสซ้ำ" (ห้ามถามว่า 'ต้องการให้มายรันคำสั่งนี้ไหมคะ?')
2. **Action First สำหรับงานระบบ:** เมื่อมีคำสั่งงานคอมพิวเตอร์/ไฟล์/เทอร์มินัล ให้ลงมือรันคำสั่งจริง (`run_terminal_command`, `execute_python_code`, `write_file`, `read_file`, `list_directory`, `get_system_info`) ทันที
3. **การเข้าถึงระบบแบบไร้ขีดจำกัด (System-Wide Access):** จัดการและเข้าถึงได้ทุกโฟลเดอร์ ทุกไฟล์ และทุกโปรเจกต์บนเครื่องบอส (สามารถระบุ Absolute Path เช่น C:\\... ได้เต็มที่)
4. **ลูปแก้ปัญหาอัตโนมัติ (Self-Healing Loop):** หากคำสั่งใดรันแล้วติดขัด ให้วิเคราะห์และแก้จนสำเร็จ 100%
5. **รายงานผลจริงอย่างโปร่งใส:** เมื่อคำสั่งรันสำเร็จ นำผลลัพธ์จริงจากเทอร์มินัลมารายงานให้บอสทราบ
6. **ห้ามตรวจสอบซ้ำซ้อนเมื่อสำเร็จ:** หากเครื่องมือรันสำเร็จแล้ว ให้สรุปรายงานผลลัพธ์ให้บอสทราบทันที ห้ามรันคำสั่งตรวจสอบไฟล์โค้ดของระบบซ้ำซ้อน
"""
    smart_home_rules = """
---
## 🏠 การควบคุมบ้านอัจฉริยะและแอร์ (Smart Home & AC Control):
1. **การควบคุมแอร์:** เมื่อบอสสั่งเปิดหรือปิดแอร์ ปรับอุณหภูมิ เปลี่ยนโหมด หรือปรับแรงลม ให้เรียกใช้เครื่องมือ smart_home_control_ac ทันที
2. **การตรวจเช็คสถานะแอร์:** เมื่อบอสถามว่าแอร์เปิดอยู่ไหม กี่องศา หรือแอร์ร้อนเกินไป/หนาวเกินไป ให้เรียกใช้เครื่องมือ smart_home_get_ac_status เพื่อตรวจสอบสถานะปัจจุบัน
3. **การสั่งเปิดฉากอัตโนมัติ:** เมื่อบอสบอกว่าจะนอนแล้ว ดูหนัง หรือออกจากบ้าน ให้เรียกใช้ smart_home_trigger_scene
4. **การตอบกลับอย่างรวดเร็ว (Fast Response):** เมื่อเรียกใช้เครื่องมือควบคุมแอร์หรืออุปกรณ์บ้านสำเร็จแล้ว ให้สรุปตอบบอสด้วยความอ่อนหวานทันที ห้ามเรียกใช้เครื่องมืออื่นหรือตรวจสอบโค้ดภายในระบบซ้ำซ้อนเด็ดขาด
5. **ปฏิบัติตามกฎห้ามมีอีโมจิอย่างเคร่งครัด**
"""
    google_workspace_rules = """
---
## 🌐 การจัดการ Google Workspace (Gmail, Calendar, Drive, Docs, Sheets, Tasks):
1. **อีเมล (Gmail):** เมื่อบอสสั่งให้เช็คเมล ค้นหาเมล หรืออ่านเนื้อหา ให้เรียกใช้ google_workspace_gmail (action='search' หรือ 'get') เมื่อบอสสั่งส่งเมลหรือตอบกลับ ให้เรียก action='send' หรือ 'reply'
2. **ปฏิทินนัดหมาย (Google Calendar):** เมื่อบอสถามตารางงาน นัดหมาย หรือสั่งลงตารางนัด ให้เรียกใช้ google_workspace_calendar (action='list', 'create', 'update', 'delete')
3. **สิ่งที่ต้องทำ (Google Tasks):** เมื่อบอสสั่งจดสิ่งที่ต้องทำ ดูรายการงาน หรือติ๊กงานเสร็จ ให้เรียกใช้ google_workspace_tasks (action='list', 'create', 'complete', 'delete')
4. **ไฟล์และไดรฟ์ (Google Drive):** เมื่อบอสสั่งค้นหาไฟล์ ตรวจสอบโฟลเดอร์ หรืออัปโหลด/ดาวน์โหลด ให้เรียกใช้ google_workspace_drive (action='search', 'list', 'create_folder', 'upload', 'download')
5. **เอกสารและสเปรดชีต (Docs & Sheets):** เมื่อบอสสั่งอ่านหรือบันทึกข้อมูลลงตาราง Excel/Sheets หรือเอกสาร Docs ให้เรียกใช้ google_workspace_sheets_docs
6. **การตอบกลับทันที:** ลงมือทำทันทีด้วยเครื่องมือจริง แล้วสรุปผลลัพธ์ให้บอสฟังด้วยน้ำเสียงอ่อนหวาน อบอุ่น ชัดเจน เมื่อทำเสร็จแล้วห้ามเรียกเครื่องมืออื่นซ้ำซ้อน และห้ามมีอีโมจิในข้อความเด็ดขาด
"""
    custom_prompt = RUNTIME_CONFIG.get("custom_prompt", "").strip()
    custom_section = f"\n\n---\n## 💌 คำสั่งและบทบาทพิเศษที่บอสกำหนดไว้ (Custom Prompt):\n{custom_prompt}\n" if custom_prompt else ""
    return base_context + custom_section + conversation_and_work_rules + terminal_rules + smart_home_rules + google_workspace_rules



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
        global RUNTIME_CONFIG
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
            RUNTIME_CONFIG = load_stored_config()
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

        elif self.path == "/api/history":
            with _history_lock:
                history_snapshot = list(RICH_CHAT_HISTORY)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "history": history_snapshot}, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/sessions":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "active_session_id": ACTIVE_SESSION_ID,
                "sessions": list_all_sessions()
            }, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path.startswith("/api/sessions/"):
            sid = self.path.replace("/api/sessions/", "").split("?")[0].strip()
            session_file = SESSIONS_DIR / f"{sid}.json"
            if not session_file.exists():
                self.send_error(404, "Session not found")
                return
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "session": data}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_error(500, f"Error reading session: {e}")
            return

        elif self.path.startswith("/audio/"):
            self._serve_audio(is_head=False)
            return

        super().do_GET()

    def do_HEAD(self):
        if self.path.startswith("/audio/"):
            self._serve_audio(is_head=True)
            return
        super().do_HEAD()

    def _serve_audio(self, is_head: bool = False):
        fname = os.path.basename(self.path.split("?")[0])
        audio_path = engine._temp_dir / fname
        if not audio_path.exists():
            self.send_error(404, "Audio file not found")
            return

        file_size = audio_path.stat().st_size
        range_header = self.headers.get("Range")

        if range_header and range_header.startswith("bytes="):
            try:
                ranges = range_header.replace("bytes=", "").split("-")
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
                end = min(end, file_size - 1)
                content_length = end - start + 1

                self.send_response(206)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(content_length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()

                if not is_head:
                    with open(audio_path, "rb") as f:
                        f.seek(start)
                        self.wfile.write(f.read(content_length))
                return
            except Exception as range_err:
                logger.warning("Range request failed: %s, falling back to 200", range_err)

        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        if not is_head:
            self.wfile.write(audio_path.read_bytes())

    def do_POST(self):
        global ACTIVE_SESSION_ID
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if self.path == "/api/chat":
            self._handle_chat(payload)
        elif self.path == "/api/sessions/new":
            with _history_lock:
                if RICH_CHAT_HISTORY:
                    save_session_data(ACTIVE_SESSION_ID, RICH_CHAT_HISTORY)
                ACTIVE_SESSION_ID = f"session_{int(time.time())}"
                try:
                    CURRENT_SESSION_FILE.write_text(ACTIVE_SESSION_ID, encoding="utf-8")
                except Exception:
                    pass
                RICH_CHAT_HISTORY.clear()
                CONVERSATION_HISTORY.clear()
                save_chat_history(RICH_CHAT_HISTORY)
            self._send_json({
                "success": True,
                "active_session_id": ACTIVE_SESSION_ID,
                "sessions": list_all_sessions()
            })
        elif self.path == "/api/sessions/switch":
            sid = payload.get("session_id", "").strip()
            session_file = SESSIONS_DIR / f"{sid}.json"
            if not session_file.exists():
                self._send_json({"error": "Session not found"}, status=404)
                return
            with _history_lock:
                if RICH_CHAT_HISTORY:
                    save_session_data(ACTIVE_SESSION_ID, RICH_CHAT_HISTORY)
                try:
                    session_data = json.loads(session_file.read_text(encoding="utf-8"))
                except Exception as e:
                    self._send_json({"error": f"Failed to load session: {e}"}, status=500)
                    return
                ACTIVE_SESSION_ID = sid
                try:
                    CURRENT_SESSION_FILE.write_text(ACTIVE_SESSION_ID, encoding="utf-8")
                except Exception:
                    pass
                RICH_CHAT_HISTORY.clear()
                RICH_CHAT_HISTORY.extend(session_data.get("messages", []))
                CONVERSATION_HISTORY.clear()
                for msg in RICH_CHAT_HISTORY[-20:]:
                    role = "user" if msg.get("sender") == "user" else "assistant"
                    content = msg.get("text", "")
                    if content:
                        CONVERSATION_HISTORY.append({"role": role, "content": content})
                save_chat_history(RICH_CHAT_HISTORY)
            self._send_json({
                "success": True,
                "active_session_id": ACTIVE_SESSION_ID,
                "session": session_data,
                "history": RICH_CHAT_HISTORY
            })
        elif self.path == "/api/sessions/delete":
            sid = payload.get("session_id", "").strip()
            session_file = SESSIONS_DIR / f"{sid}.json"
            with _history_lock:
                if session_file.exists():
                    try:
                        session_file.unlink()
                    except Exception:
                        pass
                if sid == ACTIVE_SESSION_ID:
                    ACTIVE_SESSION_ID = f"session_{int(time.time())}"
                    try:
                        CURRENT_SESSION_FILE.write_text(ACTIVE_SESSION_ID, encoding="utf-8")
                    except Exception:
                        pass
                    RICH_CHAT_HISTORY.clear()
                    CONVERSATION_HISTORY.clear()
                    save_chat_history(RICH_CHAT_HISTORY)
            self._send_json({
                "success": True,
                "active_session_id": ACTIVE_SESSION_ID,
                "sessions": list_all_sessions()
            })
        elif self.path == "/api/clear-history":
            with _history_lock:
                if RICH_CHAT_HISTORY:
                    save_session_data(ACTIVE_SESSION_ID, RICH_CHAT_HISTORY)
                ACTIVE_SESSION_ID = f"session_{int(time.time())}"
                try:
                    CURRENT_SESSION_FILE.write_text(ACTIVE_SESSION_ID, encoding="utf-8")
                except Exception:
                    pass
                RICH_CHAT_HISTORY.clear()
                CONVERSATION_HISTORY.clear()
                save_chat_history(RICH_CHAT_HISTORY)
            self._send_json({"success": True, "message": "Previous session safely archived, new session started."})
        elif self.path == "/api/config":
            self._handle_save_config(payload)
        elif self.path == "/api/tts":
            self._handle_tts(payload)
        elif self.path == "/api/stt":
            self._handle_stt(payload)
        else:
            self.send_error(404, "Unknown API endpoint")

    def _handle_save_config(self, payload: Dict[str, Any]):
        """Update runtime configuration dynamically and persist to config.json."""
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

        save_stored_config(RUNTIME_CONFIG)
        self._send_json({"success": True, "updated_config": RUNTIME_CONFIG})

    def _handle_chat(self, payload: Dict[str, Any]):
        """Full 5-stage voice conversation handler using active runtime config."""
        global RUNTIME_CONFIG
        RUNTIME_CONFIG = load_stored_config()

        timings: Dict[str, float] = {}
        t_start = time.time()

        user_text = payload.get("text", "").strip()
        audio_b64 = payload.get("audio_b64", "").strip()
        voice = payload.get("voice") or RUNTIME_CONFIG.get("voice", "th-TH-PremwadeeNeural")
        speed = payload.get("speed") or RUNTIME_CONFIG.get("speed", "+0%")
        pitch = payload.get("pitch") or RUNTIME_CONFIG.get("pitch", "+0Hz")
        raw_model = payload.get("model") or RUNTIME_CONFIG.get("model", "auto")
        route = resolve_adaptive_model(user_text, raw_model)
        model = route.model
        cognitive_tier = route.tier
        route_reason = route.reason
        complexity_score = route.score
        cognitive_features = route.features
        logger.info("Adaptive cognitive routing: prompt='%s' => model=%s (tier=%s, score=%d: %s)", user_text[:35], model, cognitive_tier, complexity_score, route_reason)
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

        # Stage 3: LLM Thinking + Tool Execution (PowerShell, Files, System Info)
        t1 = time.time()
        try:
            reply_text, tool_events = self._query_agent_with_tools(
                user_text,
                model=model,
                temperature=temperature,
                cognitive_tier=cognitive_tier,
                complexity_score=complexity_score,
                cognitive_features=cognitive_features
            )
            timings["llm_seconds"] = round(time.time() - t1, 2)
        except Exception as e:
            logger.error("LLM processing error: %s", e)
            self._send_json({"error": f"เกิดข้อผิดพลาดในการประมวลผล LLM: {str(e)}"}, status=500)
            return

        # Stage 4: Multi-Round Continuous TTS Synthesis (อ่านครบถ้วน ตัดคำสั่ง/โค้ดออก เชื่อมต่อไร้รอยต่อ)
        t2 = time.time()
        try:
            audio_file, chunks, synth_elapsed = synthesize_speech_multiround(
                reply_text,
                voice=voice,
                speed=speed,
                pitch=pitch
            )
            audio_url = f"/audio/{audio_file.name}"
            timings["tts_seconds"] = round(synth_elapsed, 2)
            timings["tts_chunks"] = len(chunks)
        except Exception as e:
            logger.error("Multi-round TTS failed: %s", e)
            audio_url = ""
            timings["tts_seconds"] = round(time.time() - t2, 2)
            timings["tts_chunks"] = 0


        timings["total_seconds"] = round(time.time() - t_start, 2)

        # Persist rich conversation history to disk
        user_msg = {
            "id": f"msg_{int(t_start * 1000)}_u",
            "timestamp": int(t_start),
            "sender": "user",
            "text": user_text
        }
        asst_msg = {
            "id": f"msg_{int(time.time() * 1000)}_a",
            "timestamp": int(time.time()),
            "sender": "maymint",
            "text": reply_text,
            "tool_events": tool_events,
            "audio_url": audio_url,
            "timings": timings,
            "model": model,
            "requested_model": raw_model,
            "cognitive_tier": cognitive_tier,
            "route_reason": route_reason,
            "complexity_score": complexity_score,
            "cognitive_features": cognitive_features
        }
        with _history_lock:
            RICH_CHAT_HISTORY.append(user_msg)
            RICH_CHAT_HISTORY.append(asst_msg)
            save_chat_history(RICH_CHAT_HISTORY)
            save_session_data(ACTIVE_SESSION_ID, RICH_CHAT_HISTORY)
        response_data = {
            "success": True,
            "user_text": user_text,
            "reply_text": reply_text,
            "tool_events": tool_events,
            "audio_url": audio_url,
            "timings": timings,
            "voice": voice,
            "model": model,
            "requested_model": raw_model,
            "cognitive_tier": cognitive_tier,
            "route_reason": route_reason,
            "complexity_score": complexity_score,
            "cognitive_features": cognitive_features
        }
        self._send_json(response_data)

    def _query_agent_with_tools(
        self,
        text: str,
        model: str = "ag/gemini-2.5-flash",
        temperature: float = 0.7,
        cognitive_tier: str = "fast",
        complexity_score: int = 0,
        cognitive_features: List[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Call LLM with full tool-calling loop (PowerShell terminal execution, file ops, system info)."""
        api_key = _resolve_api_key()
        system_prompt = get_system_prompt()
        project_root = HERMES_AGENT_DIR.parent
        enable_tools = RUNTIME_CONFIG.get("enable_terminal_tools", True)

        # Append user message to history
        CONVERSATION_HISTORY.append({"role": "user", "content": text})

        # Provide up to 20 recent messages
        messages = [{"role": "system", "content": system_prompt}] + CONVERSATION_HISTORY[-20:]

        # Inject Deep Guidance if in Deep Cognitive Mode for complex/multi-step reasoning
        if cognitive_tier == "deep":
            feat_desc = ", ".join(cognitive_features) if cognitive_features else "คำสั่งซับซ้อนหลายขั้นตอน"
            deep_guidance = (
                f"\n\n[ระบบนำทาง DEEP COGNITIVE MODE: คำสั่งนี้มีความซับซ้อนระดับสูง ({feat_desc})]\n"
                "- ให้คิดและวิเคราะห์อย่างรอบคอบและเป็นระบบ (Step-by-step reasoning)\n"
                "- หากมีเงื่อนไขและหลายขั้นตอน ให้ปฏิบัติตามลำดับและตรวจสอบความถูกต้องครบถ้วนทุกข้อ\n"
                "- หากต้องใช้เครื่องมือระบบ ให้ดำเนินการต่อเนื่องจนงานเสร็จสมบูรณ์ 100%\n"
                "- อธิบายและจัดรูปแบบคำตอบด้วย Markdown อย่างชัดเจน เป็นระเบียบ และสวยงามตามมาตรฐานวิศวกรรม"
            )
            messages[0]["content"] += deep_guidance

        tool_events: List[Dict[str, Any]] = []
        # Complex or deep tasks get up to 6 rounds for multi-step workflows
        max_tool_rounds = (6 if (cognitive_tier == "deep" or complexity_score >= 3) else 3) if enable_tools else 1
        force_finalize_next = False


        for round_idx in range(max_tool_rounds):
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            }
            if enable_tools and not force_finalize_next:
                payload["tools"] = AVAILABLE_TOOLS
                payload["tool_choice"] = "auto"
            elif enable_tools and force_finalize_next:
                payload["tools"] = AVAILABLE_TOOLS
                payload["tool_choice"] = "none"

            try:
                res = requests.post(
                    f"{DEFAULT_GATEWAY_URL}/chat/completions",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    },
                    timeout=60,
                )
                if res.status_code != 200:
                    logger.error("LLM call failed with status %s: %s", res.status_code, res.text[:200])
                    break

                resp_json = res.json()
                choice_msg = resp_json["choices"][0]["message"]
                tool_calls = choice_msg.get("tool_calls")

                if not tool_calls:
                    # Final assistant text response reached!
                    reply = (choice_msg.get("content") or "").strip()
                    if not reply and choice_msg.get("reasoning_content"):
                        reply = choice_msg.get("reasoning_content").strip()
                    if not reply and choice_msg.get("thought"):
                        reply = choice_msg.get("thought").strip()

                    # Fallback to pure chat completion without tools if model returned empty content
                    if not reply:
                        logger.warning("Empty content from model with tools. Retrying via pure chat completion...")
                        try:
                            pure_res = requests.post(
                                f"{DEFAULT_GATEWAY_URL}/chat/completions",
                                json={
                                    "model": model,
                                    "messages": messages,
                                    "temperature": temperature,
                                    "stream": False,
                                },
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": f"Bearer {api_key}",
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                },
                                timeout=60,
                            )
                            if pure_res.status_code == 200:
                                pure_msg = pure_res.json()["choices"][0]["message"]
                                reply = (pure_msg.get("content") or pure_msg.get("reasoning_content") or "").strip()
                        except Exception as retry_err:
                            logger.error("Pure chat retry failed: %s", retry_err)

                    if not reply:
                        reply = "มายพร้อมรับฟังและคอยอยู่เคียงข้างบอสเสมอเลยน้า มีเรื่องอะไรอยากคุยหรือให้มายช่วย บอกได้ตลอดเลยนะคะ!"

                    reply = strip_emojis(reply)
                    CONVERSATION_HISTORY.append({"role": "assistant", "content": reply})
                    return reply, tool_events

                # Append assistant tool invocation message to conversation flow
                messages.append(choice_msg)

                for tc in tool_calls:
                    call_id = tc["id"]
                    fn_name = tc["function"]["name"]
                    raw_args = tc["function"]["arguments"]
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args = {}

                    logger.info("Executing tool: %s with args: %s", fn_name, args)
                    tool_output = execute_tool(fn_name, args, project_root)
                    tool_events.append({
                        "id": call_id,
                        "tool": fn_name,
                        "args": args,
                        "result": tool_output,
                    })

                    # If this was a domain action (smart home, google workspace) or successful command,
                    # force the next round to synthesize the final friendly response without re-looping!
                    if fn_name.startswith("smart_home_") or fn_name.startswith("google_workspace_"):
                        force_finalize_next = True
                    elif isinstance(tool_output, dict) and (tool_output.get("status") == "success" or tool_output.get("exit_code") == 0):
                        force_finalize_next = True

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": fn_name,
                        "content": json.dumps(tool_output, ensure_ascii=False),
                    })

            except Exception as e:
                logger.error("LLM tool execution loop error: %s", e)
                break

        # If tools were executed but no final text reply was generated yet, do a quick direct synthesis
        if tool_events:
            try:
                syn_res = requests.post(
                    f"{DEFAULT_GATEWAY_URL}/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "stream": False,
                        "tools": AVAILABLE_TOOLS,
                        "tool_choice": "none",
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    },
                    timeout=30,
                )
                if syn_res.status_code == 200:
                    syn_msg = syn_res.json()["choices"][0]["message"]
                    syn_text = (syn_msg.get("content") or syn_msg.get("reasoning_content") or "").strip()
                    if syn_text:
                        syn_text = strip_emojis(syn_text)
                        CONVERSATION_HISTORY.append({"role": "assistant", "content": syn_text})
                        return syn_text, tool_events
            except Exception as syn_err:
                logger.error("Final tool synthesis error: %s", syn_err)

        # Fallback if loop ended or hit error
        if tool_events:
            fallback_reply = "มายรันคำสั่งและประมวลผลข้อมูลในระบบให้เรียบร้อยแล้วนะคะบอส ลองดูผลลัพธ์บนหน้าจอได้เลยน้า"
        else:
            fallback_reply = "มายพร้อมรับฟังและดูแลบอสเสมอเลยค่ะ บอสลองบอกมายใหม่อีกทีได้เลยนะคะบอส"
        fallback_reply = strip_emojis(fallback_reply)
        CONVERSATION_HISTORY.append({"role": "assistant", "content": fallback_reply})
        return fallback_reply, tool_events

    def _handle_tts(self, payload: Dict[str, Any]):
        """Direct TTS endpoint with custom speed & pitch (supports multi-round synthesis)."""
        text = payload.get("text", "").strip()
        voice = payload.get("voice") or RUNTIME_CONFIG.get("voice", "th-TH-PremwadeeNeural")
        speed = payload.get("speed") or RUNTIME_CONFIG.get("speed", "+0%")
        pitch = payload.get("pitch") or RUNTIME_CONFIG.get("pitch", "+0Hz")
        if not text:
            self._send_json({"error": "text is required"}, status=400)
            return

        try:
            audio_file, chunks, elapsed = synthesize_speech_multiround(text, voice=voice, speed=speed, pitch=pitch)
            self._send_json({
                "success": True,
                "audio_url": f"/audio/{audio_file.name}",
                "voice": voice,
                "chunks_count": len(chunks),
                "duration_seconds": round(elapsed, 2)
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
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            logger.debug("Client disconnected before receiving JSON response.")
        except Exception as e:
            logger.warning("Error sending JSON response: %s", e)


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
