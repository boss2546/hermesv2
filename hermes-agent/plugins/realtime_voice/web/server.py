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
import time
import urllib.request
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
    from voice_engine import engine, DEFAULT_GATEWAY_URL, _resolve_api_key  # type: ignore
except ImportError:
    from ..voice_engine import engine, DEFAULT_GATEWAY_URL, _resolve_api_key  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-server")

WEB_DIR = CURRENT_DIR
PORT = 9229
BING_CACHE: Dict[str, Any] = {"url": "", "title": "", "timestamp": 0}

# Conversational Multi-Turn Memory
CONVERSATION_HISTORY: List[Dict[str, str]] = []

# Dynamic Runtime Configuration with persistent config.txt & config.json support
CONFIG_TXT_PATH = CURRENT_DIR.parent / "config.txt"
CONFIG_PATH = HERMES_AGENT_DIR.parent / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "voice": "th-TH-PremwadeeNeural",
    "speed": "+0%",
    "pitch": "+0Hz",
    "model": "ag/gemini-2.5-flash",
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
    # Strip emojis completely so TTS won't read emoji names
    cleaned = strip_emojis(cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return "มายจัดเตรียมโค้ดและรายละเอียดทั้งหมดไว้ให้บนหน้าจอเรียบร้อยแล้วนะคะบอส"

    # If the text is longer than max_chars, take a clean sentence/phrase cut
    if len(cleaned) > max_chars:
        cut = cleaned[:max_chars]
        last_punct = max(cut.rfind("ค่ะ"), cut.rfind("นะคะ"), cut.rfind("น้า"), cut.rfind(". "), cut.rfind("!"))
        if last_punct > 120:
            cut = cut[:last_punct + 4].strip()
        else:
            cut = cut.rstrip()
        cleaned = cut + " ... มายเตรียมโค้ดและเนื้อหาทั้งหมดไว้ให้บนหน้าจอแล้วนะคะบอส ลองดูได้เลยน้า"

    return strip_emojis(cleaned)


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
"""
    smart_home_rules = """
---
## 🏠 การควบคุมบ้านอัจฉริยะและแอร์ (Smart Home & AC Control):
1. **การควบคุมแอร์:** เมื่อบอสสั่งเปิดหรือปิดแอร์ ปรับอุณหภูมิ เปลี่ยนโหมด หรือปรับแรงลม ให้เรียกใช้เครื่องมือ smart_home_control_ac ทันที
2. **การตรวจเช็คสถานะแอร์:** เมื่อบอสถามว่าแอร์เปิดอยู่ไหม กี่องศา หรือแอร์ร้อนเกินไป/หนาวเกินไป ให้เรียกใช้เครื่องมือ smart_home_get_ac_status เพื่อตรวจสอบสถานะปัจจุบัน
3. **การสั่งเปิดฉากอัตโนมัติ:** เมื่อบอสบอกว่าจะนอนแล้ว ดูหนัง หรือออกจากบ้าน ให้เรียกใช้ smart_home_trigger_scene
4. **การตอบกลับ:** ตอบรับด้วยความอบอุ่น น่ารัก อ่อนหวาน (เช่น "มายปรับแอร์เป็น 25 องศาให้แล้วนะคะบอส เย็นสบายแน่นอนน้า") และปฏิบัติตามกฎห้ามมีอีโมจิอย่างเคร่งครัด
"""
    custom_prompt = RUNTIME_CONFIG.get("custom_prompt", "").strip()
    custom_section = f"\n\n---\n## 💌 คำสั่งและบทบาทพิเศษที่บอสกำหนดไว้ (Custom Prompt):\n{custom_prompt}\n" if custom_prompt else ""
    return base_context + custom_section + conversation_and_work_rules + terminal_rules + smart_home_rules


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
        model = payload.get("model") or RUNTIME_CONFIG.get("model", "ag/gemini-2.5-flash")
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
        reply_text, tool_events = self._query_agent_with_tools(user_text, model=model, temperature=temperature)
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
            "tool_events": tool_events,
            "audio_url": audio_url,
            "timings": timings,
            "voice": voice,
            "model": model,
        }
        self._send_json(response_data)

    def _query_agent_with_tools(self, text: str, model: str = "ag/gemini-2.5-flash", temperature: float = 0.7) -> Tuple[str, List[Dict[str, Any]]]:
        """Call LLM with full tool-calling loop (PowerShell terminal execution, file ops, system info)."""
        api_key = _resolve_api_key()
        system_prompt = get_system_prompt()
        project_root = HERMES_AGENT_DIR.parent
        enable_tools = RUNTIME_CONFIG.get("enable_terminal_tools", True)

        # Append user message to history
        CONVERSATION_HISTORY.append({"role": "user", "content": text})

        # Provide up to 20 recent messages
        messages = [{"role": "system", "content": system_prompt}] + CONVERSATION_HISTORY[-20:]
        tool_events: List[Dict[str, Any]] = []
        max_tool_rounds = 6 if enable_tools else 1

        for round_idx in range(max_tool_rounds):
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            }
            if enable_tools:
                payload["tools"] = AVAILABLE_TOOLS
                payload["tool_choice"] = "auto"
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

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": fn_name,
                        "content": json.dumps(tool_output, ensure_ascii=False),
                    })

            except Exception as e:
                logger.error("LLM tool execution loop error: %s", e)
                break

        # Fallback if loop ended or hit error
        if tool_events:
            fallback_reply = "มายรันคำสั่งและประมวลผลข้อมูลในระบบให้เรียบร้อยแล้วนะคะบอส ลองดูผลลัพธ์บนหน้าจอได้เลยน้า"
        else:
            fallback_reply = "มายพร้อมรับฟังและดูแลบอสเสมอเลยค่ะ บอสลองบอกมายใหม่อีกทีได้เลยนะคะบอส"
        fallback_reply = strip_emojis(fallback_reply)
        CONVERSATION_HISTORY.append({"role": "assistant", "content": fallback_reply})
        return fallback_reply, tool_events

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
