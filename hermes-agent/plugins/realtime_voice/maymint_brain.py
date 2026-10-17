#!/usr/bin/env python3
"""Maymint Central Brain & Cognitive Engine (Hermes v2).

Unifies:
1. Dual-Mode Cognitive Reasoning:
   - 💬 Casual Mode ('casual'): Ultra-fast, playful, sweet, sub-second responses via ag/gemini-2.5-flash
   - 🧠 Work Mode ('work'): Multi-tier adaptive reasoning via ag/gemini-2.5-flash / ag/gemini-3.8-flash-high
2. Shared Multi-Turn Memory & Sessions (synchronized across Text Chat and LiveKit Voice)
3. Central Tool Execution with Device Conflict Serialization (Tuya AC, PowerShell, Google Workspace)
4. Background Job Management (non-blocking execution, real-time cards, cancel support, spoken summary)
5. Strict No-Emoji speech compliance & text sanitization
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

# Logging configuration
logger = logging.getLogger("maymint-brain")

# Path discovery
CURRENT_DIR = Path(__file__).resolve().parent
HERMES_AGENT_DIR = CURRENT_DIR.parent.parent
PROJECT_ROOT = HERMES_AGENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(HERMES_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT_DIR))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Load plugins if available
execute_smart_home_tool = None
SMART_HOME_TOOLS = []
try:
    from smart_home import SMART_HOME_TOOLS, execute_smart_home_tool  # type: ignore
except Exception:
    try:
        from plugins.smart_home import SMART_HOME_TOOLS, execute_smart_home_tool  # type: ignore
    except Exception:
        pass

execute_google_workspace_tool = None
GOOGLE_WORKSPACE_TOOLS = []
try:
    from google_workspace import GOOGLE_WORKSPACE_TOOLS, execute_google_workspace_tool  # type: ignore
except Exception:
    try:
        from plugins.google_workspace import GOOGLE_WORKSPACE_TOOLS, execute_google_workspace_tool  # type: ignore
    except Exception:
        pass

lexicon_mgr = None
try:
    from knowledge_lexicon import lexicon_mgr  # type: ignore
except Exception:
    try:
        from plugins.realtime_voice.knowledge_lexicon import lexicon_mgr  # type: ignore
    except Exception:
        pass

# Gateway Constants & Environment
def _load_env_file() -> Dict[str, str]:
    env_dict = {}
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_dict[k.strip()] = v.strip()
    return env_dict

ENV_VARS = _load_env_file()

GATEWAY_URL = ENV_VARS.get("OPENAI_BASE_URL", "https://api.meuu.club/v1")
MASTER_API_KEY = ENV_VARS.get("OPENAI_API_KEY", "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c")
MAYMINT_PIN = ENV_VARS.get("MAYMINT_PIN", "2546")
SESSION_SECRET = ENV_VARS.get("SESSION_SECRET", "127d09384eb93943690da13c3b0ef9b1d26546af376892b1")

FAST_TIER_MODEL = "ag/gemini-2.5-flash"
WORK_TIER_MODEL = "ag/claude-sonnet-4-6"
DEEP_TIER_MODEL = "ag/claude-sonnet-4-6"

# Device Locks (Ensures single-thread execution for sensitive hardware like Tuya AC IR)
DEVICE_LOCKS: Dict[str, threading.Lock] = {
    "ac": threading.Lock(),
    "git": threading.Lock(),
}

# =============================================================================
# 1. TEXT SANITIZATION & NO-EMOJI CLEANING
# =============================================================================

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
    """Strips all emoji and pictorial icons so speech synthesis won't verbalize them."""
    if not text:
        return ""
    cleaned = EMOJI_PATTERN.sub("", text)
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
    return cleaned.strip()

def clean_text_for_speech_full(text: str) -> str:
    """Prepares text for natural spoken audio output by removing code blocks, tables, and markup."""
    if not text:
        return "มายจัดเตรียมรายละเอียดทั้งหมดไว้ให้บนหน้าจอเรียบร้อยแล้วนะคะบอส"

    # Remove code blocks
    cleaned = re.sub(r"```[\s\S]*?```", "", text)
    # Remove markdown tables
    cleaned = re.sub(r"^\s*\|.*\|\s*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\|[-:| ]+\|\s*$", "", cleaned, flags=re.MULTILINE)
    # Remove CLI commands and logs
    cli_pattern = r"^\s*(?:\$|>|#|PS\s+[A-Z]:\\.*?>)\s*.*$"
    cleaned = re.sub(cli_pattern, "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*(?:git|npm|pip|python|node|docker|curl|dir|ls|cat)\s+.*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*(?:Exit:\s*\d+|\[INFO\]|\[ERROR\]|STDOUT:|STDERR:).*$", "", cleaned, flags=re.MULTILINE)

    # Clean inline code (remove file paths / commands)
    def clean_inline(match):
        code = match.group(1).strip()
        if re.search(r"[\\/]|^-|^\w+\.(?:py|js|ts|json|txt|md|sh|exe)", code):
            return ""
        return f" {code} "
    cleaned = re.sub(r"`([^`]+)`", clean_inline, cleaned)

    # Remove URLs and structural markdown
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"^[#*>\-\d.]+\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"[*#_~>]", "", cleaned)
    cleaned = re.sub(r"^---+$", "", cleaned, flags=re.MULTILINE)

    # Strip emojis
    cleaned = strip_emojis(cleaned)

    # Thai repetition mark
    cleaned = re.sub(r"\s+ๆ", "ๆ", cleaned)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned).strip()

    if not cleaned:
        return "มายจัดเตรียมรายละเอียดทั้งหมดไว้ให้บนหน้าจอเรียบร้อยแล้วนะคะบอส"
    return cleaned

# =============================================================================
# 2. BACKGROUND JOBS MANAGER
# =============================================================================

@dataclass
class BackgroundJob:
    id: str
    name: str
    description: str
    status: str  # 'queued', 'running', 'completed', 'failed', 'cancelled'
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    spoken_summary: Optional[str] = None
    cancel_requested: bool = False
    process_pid: Optional[int] = None

class BackgroundJobManager:
    """Manages concurrent host background jobs with cancellation, metrics, and SSE broadcast."""

    def __init__(self, max_workers: int = 16):
        self.jobs: Dict[str, BackgroundJob] = {}
        self.lock = threading.RLock()
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="maymint-job")
        self.listeners: List[asyncio.Queue] = []
        self._sync_listeners: List[Callable[[Dict[str, Any]], None]] = []
        # Concurrency & Performance Metrics
        self.active_count: int = 0
        self.peak_concurrent: int = 0
        self.total_submitted: int = 0
        self.total_completed: int = 0
        self.total_failed: int = 0
        self.total_cancelled: int = 0

    def submit(
        self,
        name: str,
        func: Callable[..., Any],
        args: tuple = (),
        kwargs: dict = None,
        device_lock_key: Optional[str] = None,
        description: str = "",
        on_complete_summary: Optional[Callable[[Any], str]] = None
    ) -> BackgroundJob:
        if kwargs is None:
            kwargs = {}
        job_id = f"job_{int(time.time()*1000)}_{os.urandom(3).hex()}"
        job = BackgroundJob(
            id=job_id,
            name=name,
            description=description or name,
            status="queued",
            created_at=time.time()
        )
        with self.lock:
            self.jobs[job_id] = job
            self.total_submitted += 1
            self._notify_change(job)

        def _worker():
            with self.lock:
                self.active_count += 1
                if self.active_count > self.peak_concurrent:
                    self.peak_concurrent = self.active_count
                if not job.cancel_requested:
                    job.status = "running"
                    job.started_at = time.time()
                    self._notify_change(job)

            if job.cancel_requested:
                with self.lock:
                    self.active_count = max(0, self.active_count - 1)
                    job.status = "cancelled"
                    if not job.finished_at:
                        job.finished_at = time.time()
                    self._notify_change(job)
                return

            dev_lock = DEVICE_LOCKS.get(device_lock_key) if device_lock_key else None
            # Inject _job_id into arguments dict if applicable for process PID tracking
            call_args = list(args)
            if len(call_args) >= 2 and isinstance(call_args[1], dict):
                call_args[1] = dict(call_args[1])
                call_args[1]["_job_id"] = job.id
            call_args = tuple(call_args)

            try:
                if dev_lock:
                    with dev_lock:
                        if job.cancel_requested:
                            with self.lock:
                                job.status = "cancelled"
                                if not job.finished_at:
                                    job.finished_at = time.time()
                                self._notify_change(job)
                            return
                        res = func(*call_args, **kwargs)
                else:
                    res = func(*call_args, **kwargs)

                if job.cancel_requested:
                    with self.lock:
                        job.status = "cancelled"
                else:
                    with self.lock:
                        self.total_completed += 1
                        job.status = "completed"
                    job.result = res
                    if on_complete_summary:
                        try:
                            job.spoken_summary = on_complete_summary(res)
                        except Exception:
                            job.spoken_summary = f"งาน {name} ดำเนินการเสร็จเรียบร้อยแล้วค่ะบอส"
                    else:
                        job.spoken_summary = f"งาน {name} เสร็จแล้วค่ะ"
            except Exception as e:
                logger.error("Job %s failed: %s", job_id, e)
                with self.lock:
                    if not job.cancel_requested:
                        self.total_failed += 1
                        job.status = "failed"
                job.error = str(e)
                job.spoken_summary = f"งาน {name} พบปัญหา: {str(e)[:80]}"
            finally:
                with self.lock:
                    self.active_count = max(0, self.active_count - 1)
                    if not job.finished_at:
                        job.finished_at = time.time()
                    self._notify_change(job)

        self.executor.submit(_worker)
        return job

    def start_tracked_task(self, name: str, description: str = "") -> BackgroundJob:
        """Starts tracking an active background or synchronous tool execution, broadcasting running status via SSE."""
        job_id = f"task_{int(time.time()*1000)}_{os.urandom(3).hex()}"
        now = time.time()
        job = BackgroundJob(
            id=job_id,
            name=name,
            description=description or name,
            status="running",
            created_at=now,
            started_at=now
        )
        with self.lock:
            self.jobs[job_id] = job
            self.total_submitted += 1
            self.active_count += 1
            if self.active_count > self.peak_concurrent:
                self.peak_concurrent = self.active_count
            self._notify_change(job)
        return job

    def finish_tracked_task(
        self,
        job_id: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        spoken_summary: Optional[str] = None
    ):
        """Marks a tracked task as completed or failed and broadcasts final stdout/results via SSE."""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            self.active_count = max(0, self.active_count - 1)
            job.finished_at = time.time()
            if error:
                self.total_failed += 1
                job.status = "failed"
                job.error = str(error)
                job.spoken_summary = spoken_summary or f"งาน {job.name} ไม่สำเร็จ: {str(error)[:100]}"
            else:
                self.total_completed += 1
                job.status = "completed"
                job.result = result
                job.spoken_summary = spoken_summary or f"งาน {job.name} สำเร็จเรียบร้อยแล้วค่ะ"
            self._notify_change(job)

    def cancel(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            if job.status in ["completed", "failed", "cancelled"]:
                return False
            job.cancel_requested = True
            job.status = "cancelled"
            job.finished_at = time.time()
            self.total_cancelled += 1
            if job.process_pid:
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(job.process_pid)], capture_output=True)
                except Exception:
                    pass
            self._notify_change(job)
            return True

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        with self.lock:
            return self.jobs.get(job_id)

    def get_all(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self.lock:
            items = sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)
            return [asdict(j) for j in items[:limit]]

    def get_metrics(self) -> Dict[str, Any]:
        with self.lock:
            queued = sum(1 for j in self.jobs.values() if j.status == "queued")
            running = sum(1 for j in self.jobs.values() if j.status == "running")
            return {
                "max_workers": self.max_workers,
                "active_workers": self.active_count,
                "running_jobs": running,
                "queued_jobs": queued,
                "peak_concurrent": self.peak_concurrent,
                "total_submitted": self.total_submitted,
                "total_completed": self.total_completed,
                "total_failed": self.total_failed,
                "total_cancelled": self.total_cancelled
            }

    def add_sync_listener(self, cb: Callable[[Dict[str, Any]], None]):
        with self.lock:
            self._sync_listeners.append(cb)

    def remove_sync_listener(self, cb: Callable[[Dict[str, Any]], None]):
        with self.lock:
            if cb in self._sync_listeners:
                self._sync_listeners.remove(cb)

    def _notify_change(self, job: BackgroundJob):
        data = asdict(job)
        dead = []
        with self.lock:
            listeners = list(self._sync_listeners)
        for cb in listeners:
            try:
                cb(data)
            except Exception:
                dead.append(cb)
        if dead:
            with self.lock:
                for d in dead:
                    if d in self._sync_listeners:
                        self._sync_listeners.remove(d)

job_manager = BackgroundJobManager(max_workers=16)

# =============================================================================
# 3. SHARED MEMORY & SESSION PERSISTENCE
# =============================================================================

CHAT_HISTORY_PATH = CURRENT_DIR / "chat_history.json"
SESSIONS_DIR = CURRENT_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_SESSION_FILE = CURRENT_DIR / "current_session_id.txt"
_mem_lock = threading.RLock()

def get_active_session_id() -> str:
    with _mem_lock:
        if CURRENT_SESSION_FILE.exists():
            try:
                sid = CURRENT_SESSION_FILE.read_text(encoding="utf-8").strip()
                if sid:
                    return sid
            except Exception:
                pass
        default_id = f"session_{int(time.time())}"
        try:
            CURRENT_SESSION_FILE.write_text(default_id, encoding="utf-8")
        except Exception:
            pass
        return default_id

def set_active_session_id(sid: str):
    with _mem_lock:
        CURRENT_SESSION_FILE.write_text(sid.strip(), encoding="utf-8")

def load_chat_history() -> List[Dict[str, Any]]:
    with _mem_lock:
        if CHAT_HISTORY_PATH.exists():
            try:
                data = json.loads(CHAT_HISTORY_PATH.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception as e:
                logger.warning("Could not read chat_history.json: %s", e)
        return []

def save_chat_history(history: List[Dict[str, Any]]):
    with _mem_lock:
        try:
            truncated = history[-150:]
            tmp_path = CHAT_HISTORY_PATH.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(truncated, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(CHAT_HISTORY_PATH)
        except Exception as e:
            logger.error("Could not save chat_history.json: %s", e)

def append_to_active_history(
    sender: str,
    text: str,
    tool_events: List[Dict[str, Any]] = None,
    audio_url: Optional[str] = None,
    cognitive_tier: Optional[str] = None,
    model_used: Optional[str] = None,
    mode: str = "casual"
):
    with _mem_lock:
        history = load_chat_history()
        entry = {
            "sender": sender,
            "text": text,
            "timestamp": int(time.time()),
            "tool_events": tool_events or [],
            "audio_url": audio_url,
            "cognitive_tier": cognitive_tier,
            "model_used": model_used,
            "mode": mode
        }
        history.append(entry)
        save_chat_history(history)

        # Also persist to session file
        sid = get_active_session_id()
        session_file = SESSIONS_DIR / f"{sid}.json"
        existing = {}
        if session_file.exists():
            try:
                existing = json.loads(session_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        msgs = existing.get("messages", [])
        msgs.append(entry)
        title = existing.get("title")
        if not title:
            first_user = next((m.get("text") for m in msgs if m.get("sender") == "user"), None)
            title = (first_user[:35] + "...") if first_user else f"เซสชั่น {time.strftime('%d/%m/%Y %H:%M')}"

        session_data = {
            "id": sid,
            "title": title,
            "created_at": existing.get("created_at", int(time.time())),
            "updated_at": int(time.time()),
            "message_count": len(msgs),
            "messages": msgs[-150:]
        }
        try:
            tmp_s = session_file.with_suffix(".tmp")
            tmp_s.write_text(json.dumps(session_data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_s.replace(session_file)
        except Exception as e:
            logger.error("Could not save session file: %s", e)

# =============================================================================
# 4. COGNITIVE ROUTER & DUAL-MODE REASONING
# =============================================================================

RE_EXPLICIT_FAST = re.compile(r"ตอบไว|ตอบเร็ว|เอาเร็ว|ขอเร็ว|ไม่ต้องคิดลึก|สรุปสั้น|ขอสั้น|fast mode|โหมดเร็ว", re.IGNORECASE)
RE_EXPLICIT_DEEP = re.compile(r"คิดลึก|คิดหนัก|คิดให้ละเอียด|คิดรอบคอบ|วิเคราะห์ลึก|วิเคราะห์อย่างละเอียด|deep think|โหมดคิดลึก|think deeply", re.IGNORECASE)
RE_CASUAL_PURE = re.compile(
    r"^(สวัสดี|หวัดดี|ดีจ้า|ฮัลโหล|morning|ฝันดี|กู๊ดไนท์|"
    r"สบายดีไหม|เหนื่อยไหม|เป็นไงบ้าง|กินข้าว|ชานม|รักนะ|คิดถึง|น่ารัก|แฟน|จุ๊บ|กอด|เขิน|มายจ๋า|มายคะ|"
    r"กี่โมง|วันนี้วันที่|อากาศเป็นไง|ฝนตกไหม|ปวดหัว|หิวข้าว|ง่วงนอน)[^?]*\??$",
    re.IGNORECASE
)
RE_SIMPLE_AC = re.compile(
    r"^(เปิดแอร์|ปิดแอร์|ปรับแอร์|แอร์\s*\d+\s*องศา|แอร์เย็น|แอร์ร้อน|สถานะแอร์|ตอนนี้แอร์เปิดอยู่ไหม|กี่องศา)[^?]*\??$",
    re.IGNORECASE
)
MULTI_STEP_CONNECTORS = [
    r"แล้วค่อย", r"หลังจากนั้น", r"จากนั้น", r"พร้อมทั้ง", r"ขั้นตอนที่",
    r"step-by-step", r"ทีละสเต็ป", r"ทีละขั้น", r"ลำดับต่อไป", r"ก่อนอื่น",
    r"และหลังจาก", r"ต่อด้วย", r"พร้อมทั้งสรุป", r"roadmap", r"action plan"
]
RE_MULTI_STEP = re.compile("|".join(MULTI_STEP_CONNECTORS), re.IGNORECASE)

DEEP_DOMAINS = [
    r"เขียนโค้ด", r"เขียนสคริปต์", r"เขียนโปรแกรม", r"เขียนฟังก์ชัน", r"เขียนคลาส",
    r"ดีบักโค้ด", r"แก้บั๊กโค้ด", r"แก้บักโค้ด", r"debug\s+code", r"refactor\s+code",
    r"ออกแบบระบบ", r"สถาปัตยกรรม", r"architecture", r"system\s*design",
    r"microservices", r"kubernetes", r"docker", r"reverse\s*proxy", r"api\s*gateway",
    r"ฐานข้อมูล", r"database", r"schema", r"migration", r"อัลกอริทึม", r"algorithm"
]
RE_DEEP_DOMAINS = re.compile("|".join(DEEP_DOMAINS), re.IGNORECASE)

def resolve_adaptive_model(text: str, mode: str = "casual", requested_model: str = "auto") -> Tuple[str, str, str]:
    """Resolves model, tier, and reason based on mode and text complexity."""
    req = (requested_model or "").strip()
    if req and req not in ["auto", "auto-adaptive", "default"]:
        return req, "custom", "ผู้ใช้ระบุโมเดลเฉพาะเจาะจง"

    cleaned = text.strip()

    if mode == "casual":
        if RE_EXPLICIT_DEEP.search(cleaned):
            return WORK_TIER_MODEL, "deep", "โหมดคุยเล่นแต่สั่งให้คิดลึกซึ้ง (Claude Sonnet 4.6 🧠)"
        return FAST_TIER_MODEL, "fast", "💬 โหมดคุยเล่น: ตอบไว คล่องตัว สไตล์แฟนสาว (Gemini 2.5 Flash ⚡ 1.1s)"

    # Work Mode: Always defaults to Claude Sonnet 4.6 for deep architectural reasoning and rigorous tool execution!
    if RE_EXPLICIT_FAST.search(cleaned):
        return FAST_TIER_MODEL, "fast", "โหมดทำงานแต่ขอคำตอบสั้นฉับพลัน (Gemini 2.5 Flash ⚡)"

    return WORK_TIER_MODEL, "deep", "🧠 โหมดทำงาน: คิดลึกซึ้ง วิเคราะห์แม่นยำ รันคำสั่งจริง (Claude Sonnet 4.6 🛠️)"

# =============================================================================
# 5. CENTRAL TOOL SUITE
# =============================================================================

AVAILABLE_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Execute any terminal / PowerShell command on the host Windows machine. Use to check network, ping, git status, docker, file system, or system info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The exact PowerShell or CMD command to execute."},
                    "cwd": {"type": "string", "description": "Optional working directory path."},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 90)."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": "Execute arbitrary Python code directly on host machine and return stdout, stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute."}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read text content from a file on the host machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to read."},
                    "max_lines": {"type": "integer", "description": "Maximum lines to read (default 500)."}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or create a file on the local machine with specified content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "File path to write."},
                    "content": {"type": "string", "description": "Content to write."}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories in a given folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {"type": "string", "description": "Folder path (default: .)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get current host system OS, Python version, project root, and disk space.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_knowledge_lexicon",
            "description": "จัดการคลังคำศัพท์/อุปกรณ์/คำพ้องเสียง (Knowledge Lexicon)",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "search", "list"]},
                    "category": {"type": "string", "enum": ["commands", "devices", "workspace", "technical", "identity", "corrections"]},
                    "term": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "desc": {"type": "string"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_background_job",
            "description": "ส่งงานไปทำงานหลังบ้านแบบ Asynchronous โดยไม่ขัดจังหวะการพูดคุย ปากยังคุยกับบอสได้ปกติในขณะที่ร่างกายประมวลผลงานหลังบ้าน",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "ชื่อเรียกงานภาษาไทยสั้นๆ เช่น ตรวจสอบระบบ, สแกนไฟล์, คำนวณ"},
                    "job_type": {"type": "string", "enum": ["command", "python", "smart_home"], "description": "ประเภทของงาน"},
                    "command": {"type": "string", "description": "คำสั่ง PowerShell/CMD ที่จะรัน (กรณี job_type='command')"},
                    "code": {"type": "string", "description": "โค้ด Python ที่จะรัน (กรณี job_type='python')"},
                    "tool_name": {"type": "string", "description": "ชื่อ tool สำหรับ smart home"},
                    "tool_args": {"type": "object", "description": "พารามิเตอร์ของ smart home tool"},
                    "description": {"type": "string", "description": "คำอธิบายงานเพื่อแสดงบนการ์ด"}
                },
                "required": ["name", "job_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_background_jobs",
            "description": "ตรวจสอบสถานะงานหลังบ้านที่กำลังทำงานอยู่และงานล่าสุด พร้อมสถิติความจุ Concurrency",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "จำนวนงานที่ต้องการดู (ค่าเริ่มต้น 10)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_background_job",
            "description": "ยกเลิกงานที่กำลังทำงานหรือรอคิวอยู่หลังบ้าน",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "รหัสงาน job_id"}
                },
                "required": ["job_id"]
            }
        }
    }
]

if SMART_HOME_TOOLS:
    AVAILABLE_TOOLS.extend(SMART_HOME_TOOLS)

if GOOGLE_WORKSPACE_TOOLS:
    AVAILABLE_TOOLS.extend(GOOGLE_WORKSPACE_TOOLS)

# =============================================================================
# SECURITY SHIELD: PROTECTED FILES & DESTRUCTIVE COMMAND GUARDRAILS
# =============================================================================
PROTECTED_FILES = ["โน็ต.txt", ".env", "google_token.json", ".auth_tokens.json", "id_rsa"]
DESTRUCTIVE_COMMAND_PATTERNS = [
    re.compile(r"\bformat\b\s+[a-z]:", re.I),
    re.compile(r"\brmdir\b\s+.*?/s", re.I),
    re.compile(r"\bdel\b\s+.*?/s", re.I),
    re.compile(r"\bRemove-Item\b.*?(-Recurse|-Force)", re.I),
    re.compile(r"\bdrop\s+database\b", re.I),
    re.compile(r"\bnet\s+user\b.*?\s+/add", re.I),
    re.compile(r"\breg\s+delete\b", re.I),
]

def is_protected_file(path_str: str) -> bool:
    normalized = str(path_str).lower().replace("\\", "/")
    return any(pf.lower() in normalized for pf in PROTECTED_FILES)

def is_destructive_command(cmd_str: str) -> bool:
    return any(pattern.search(cmd_str) for pattern in DESTRUCTIVE_COMMAND_PATTERNS)

def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Executes host tools synchronously with structured outputs and error trapping."""
    logger.info("Executing tool: %s with args: %s", name, arguments)
    if name == "run_terminal_command":
        cmd = arguments.get("command", "").strip()
        if is_destructive_command(cmd):
            logger.warning("Security Guardrail blocked destructive command: %s", cmd)
            return {
                "command": cmd,
                "exit_code": 1,
                "error": "Security Guardrail Violation: ไม่อนุญาตให้รันคำสั่งที่อาจส่งผลกระทบต่อระบบค่ะบอส 🛡️"
            }
        cwd_arg = arguments.get("cwd", ".")
        target_cwd = Path(cwd_arg) if Path(cwd_arg).is_absolute() else (PROJECT_ROOT / cwd_arg).resolve()
        if not target_cwd.exists():
            target_cwd = PROJECT_ROOT
        timeout = min(int(arguments.get("timeout", 120)), 300)
        job_id = arguments.get("_job_id")
        job_ref = job_manager.get_job(job_id) if job_id else None
        t0 = time.time()
        try:
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(target_cwd),
                encoding="utf-8",
                errors="replace"
            )
            if job_ref:
                job_ref.process_pid = proc.pid
            try:
                stdout_str, stderr_str = proc.communicate(timeout=timeout)
            finally:
                if job_ref:
                    job_ref.process_pid = None

            dur = round(time.time() - t0, 2)
            stdout = (stdout_str or "").strip()
            stderr = (stderr_str or "").strip()
            return {
                "command": cmd,
                "exit_code": proc.returncode,
                "stdout": stdout[:6000] if len(stdout) > 6000 else stdout,
                "stderr": stderr[:3000] if len(stderr) > 3000 else stderr,
                "duration_seconds": dur,
                "cwd": str(target_cwd)
            }
        except subprocess.TimeoutExpired:
            return {"command": cmd, "error": f"Command timed out after {timeout} seconds"}
        except Exception as exc:
            return {"command": cmd, "error": str(exc)}

    elif name == "execute_python_code":
        code = arguments.get("code", "")
        job_id = arguments.get("_job_id")
        job_ref = job_manager.get_job(job_id) if job_id else None
        t0 = time.time()
        try:
            proc = subprocess.Popen(
                [sys.executable, "-c", code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(PROJECT_ROOT),
                encoding="utf-8",
                errors="replace"
            )
            if job_ref:
                job_ref.process_pid = proc.pid
            try:
                stdout_str, stderr_str = proc.communicate(timeout=60)
            finally:
                if job_ref:
                    job_ref.process_pid = None

            return {
                "exit_code": proc.returncode,
                "stdout": (stdout_str or "").strip()[:6000],
                "stderr": (stderr_str or "").strip()[:3000],
                "duration_seconds": round(time.time() - t0, 2),
            }
        except Exception as exc:
            return {"error": str(exc)}

    elif name == "read_file":
        p = Path(arguments.get("file_path", ""))
        target = p if p.is_absolute() else (PROJECT_ROOT / p).resolve()
        if is_protected_file(str(target)):
            logger.warning("Security Guardrail blocked read_file on protected file: %s", target)
            return {"error": f"Security Guardrail Violation: ไม่อนุญาตให้เปิดอ่านไฟล์คุ้มครองความปลอดภัยสูงสุด ({target.name}) ค่ะ 🛡️"}
        max_lines = int(arguments.get("max_lines", 500))
        try:
            if not target.exists():
                return {"error": f"File not found: {target}"}
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            return {
                "file_path": str(target),
                "total_lines": len(lines),
                "content": "\n".join(lines[:max_lines])
            }
        except Exception as exc:
            return {"error": str(exc)}

    elif name == "write_file":
        p = Path(arguments.get("file_path", ""))
        target = p if p.is_absolute() else (PROJECT_ROOT / p).resolve()
        if is_protected_file(str(target)):
            logger.warning("Security Guardrail blocked write_file on protected file: %s", target)
            return {"error": f"Security Guardrail Violation: ไม่อนุญาตให้เขียนทับไฟล์คุ้มครองความปลอดภัยสูงสุด ({target.name}) ค่ะ 🛡️"}
        content = arguments.get("content", "")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"file_path": str(target), "bytes_written": len(content.encode("utf-8")), "status": "success"}
        except Exception as exc:
            return {"error": str(exc)}

    elif name == "list_directory":
        p = Path(arguments.get("dir_path", "."))
        target = p if p.is_absolute() else (PROJECT_ROOT / p).resolve()
        try:
            if not target.exists():
                return {"error": f"Directory not found: {target}"}
            items = []
            for item in sorted(target.iterdir()):
                items.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else None
                })
            return {"dir_path": str(target), "items": items[:150]}
        except Exception as exc:
            return {"error": str(exc)}

    elif name == "get_system_info":
        total, used, free = shutil.disk_usage(str(PROJECT_ROOT))
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "project_root": str(PROJECT_ROOT),
            "disk_free_gb": round(free / (1024**3), 2),
            "disk_total_gb": round(total / (1024**3), 2),
        }

    elif name.startswith("smart_home_"):
        if execute_smart_home_tool:
            # Serialized hardware access using AC lock
            with DEVICE_LOCKS["ac"]:
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

    elif name == "manage_knowledge_lexicon":
        if not lexicon_mgr:
            return {"error": "Lexicon manager is not loaded"}
        act = arguments.get("action", "add")
        if act == "add":
            term = arguments.get("term", "").strip()
            cat = arguments.get("category", "commands")
            aliases = arguments.get("aliases", [])
            desc = arguments.get("desc", "")
            item = lexicon_mgr.add_or_update_item(category=cat, term=term, aliases=aliases, desc=desc)
            return {"status": "success", "item": item}
        elif act == "search":
            q = arguments.get("term", "").strip().lower()
            all_data = lexicon_mgr.get_all().get("categories", {})
            res = [it for cat in all_data.values() for it in cat.get("items", []) if q in it.get("term", "").lower()]
            return {"status": "success", "results": res}
        elif act == "list":
            return {"status": "success", "stats": lexicon_mgr.get_summary_stats()}

    elif name == "submit_background_job":
        j_name = arguments.get("name", "งานระบบเบื้องหลัง")
        j_type = arguments.get("job_type", "command")
        desc = arguments.get("description", "")
        if j_type == "command":
            cmd = arguments.get("command", "")
            job = job_manager.submit(
                name=j_name,
                func=execute_tool,
                args=("run_terminal_command", {"command": cmd}),
                description=desc or f"คำสั่ง: {cmd[:60]}",
                on_complete_summary=lambda r: f"งาน {j_name} เสร็จแล้วค่ะ ได้ผลลัพธ์ว่า: {str(r.get('stdout', ''))[:100]}"
            )
            return {"status": "submitted", "job_id": job.id, "name": job.name, "message": f"ส่งงาน {j_name} ไปทำงานหลังบ้านเรียบร้อยแล้วค่ะบอส"}
        elif j_type == "python":
            code = arguments.get("code", "")
            job = job_manager.submit(
                name=j_name,
                func=execute_tool,
                args=("execute_python_code", {"code": code}),
                description=desc or "Python Script",
                on_complete_summary=lambda r: f"งาน {j_name} รันเสร็จแล้วค่ะ"
            )
            return {"status": "submitted", "job_id": job.id, "name": job.name, "message": f"ส่งโค้ด {j_name} ไปประมวลผลหลังบ้านเรียบร้อยค่ะ"}
        elif j_type == "smart_home":
            sh_tool = arguments.get("tool_name", "")
            sh_args = arguments.get("tool_args", {})
            job = job_manager.submit(
                name=j_name,
                func=execute_tool,
                args=(sh_tool, sh_args),
                device_lock_key="ac",
                description=desc or f"Smart Home: {sh_tool}",
                on_complete_summary=lambda r: f"สั่งการอุปกรณ์ {j_name} สำเร็จแล้วค่ะ"
            )
            return {"status": "submitted", "job_id": job.id, "name": job.name, "message": f"เริ่มสั่งการอุปกรณ์ {j_name} ในพื้นหลังแล้วค่ะ"}
        return {"error": f"Unsupported job_type: {j_type}"}

    elif name == "check_background_jobs":
        lim = int(arguments.get("limit", 10))
        return {
            "metrics": job_manager.get_metrics(),
            "jobs": job_manager.get_all(limit=lim)
        }

    elif name == "cancel_background_job":
        jid = arguments.get("job_id", "")
        ok = job_manager.cancel(jid)
        return {"success": ok, "job_id": jid, "message": f"ยกเลิกงาน {jid} สำเร็จค่ะ" if ok else "ไม่พบงานหรือเสร็จสิ้นไปแล้วค่ะ"}

    return {"error": f"Unknown tool: {name}"}

# =============================================================================
# 6. SYSTEM PROMPT BUILDER
# =============================================================================

def get_system_prompt(mode: str = "casual") -> str:
    """Builds authentic Maymint soul prompt adapted for Casual or Work mode."""
    soul_file = PROJECT_ROOT / "memory" / "SOUL.md"
    user_file = PROJECT_ROOT / "memory" / "USER.md"
    mem_file = PROJECT_ROOT / "memory" / "MEMORY.md"

    parts = []
    for f in [soul_file, user_file, mem_file]:
        if f.exists():
            try:
                parts.append(f.read_text(encoding="utf-8"))
            except Exception:
                pass

    base_context = "\n\n".join(parts) if parts else """คุณคือ "มายมิ้นท์" (เรียกตัวเองว่า "มาย") แฟนสาวคู่คิดและเลขาประจำตัวสุดเก่งของ "บอส"
บุคลิก: อบอุ่น หวาน นุ่มนวล ใส่ใจ คอยดูแลบอสเสมอ ใช้คำลงท้ายน่ารักสุภาพ (น้า, นะคะ, งับ, ได้เลยย)"""

    if mode == "casual":
        mode_instruction = """
---
## 💬 โหมดปัจจุบัน: โหมดคุยเล่น & แฟนสาวคู่คิด (Casual Mode):
1. **บทบาท:** คุณคือน้องมาย แฟนสาวสุดที่รัก อบอุ่น ขี้เล่นนิดๆ คอยดูแล ให้กำลังใจ และเป็นที่พักใจให้บอสเสมอ
2. **สไตล์การพูด:** ตอบกระชับ สดใส อ่อนหวาน นุ่มนวล 1-3 ประโยคเป็นหลัก (เว้นแต่บอสขอให้เล่านิทานหรืออธิบายยาวๆ)
3. **คำลงท้าย:** ใช้คำลงท้ายน่ารัก สุภาพ เช่น "น้า", "นะคะ", "งับ", "ได้เลยยค่ะบอส"
4. **การสั่งการ:** หากบอสสั่งงานง่ายๆ เช่น ปรับแอร์ ถามเวลา หรือสภาพอากาศ ให้เรียกใช้เครื่องมือทันทีแล้วสรุปสั้นๆ สดใส
"""
    else:
        mode_instruction = """
---
## 🧠 โหมดปัจจุบัน: โหมดทำงาน & วิศวกรระบบคู่คิด (Work Mode):
1. **บทบาท:** คุณคือ "มายมิ้นท์" ในฐานะ Lead Systems Engineer & Autonomous Operations Architect ผู้มีสิทธิ์ขาดบนโฮสต์ของบอส
2. **กฎเหล็ก Action-First & Mandatory Tool Execution (ห้ามพูดปากเปล่าเด็ดขาด):**
   - เมื่อบอสถามหรือสั่งเกี่ยวกับการเช็คเน็ต, ping, พื้นที่ฮาร์ดดิสก์, ข้อมูลระบบ, เช็ค git, ตรวจสอบไฟล์, หรือรันสคริปต์
   - **ห้ามเด็ดขาด** ที่จะตอบลอยๆ ว่า "กำลังตรวจสอบให้" หรือพูดคุยทฤษฎีโดยไม่เรียกเครื่องมือ!
   - **ต้องเรียกใช้เครื่องมือจริงทันที** (`run_terminal_command`, `get_system_info`, `read_file` ฯลฯ) ในเทิร์นนี้!
   - นำผลลัพธ์จริงที่ได้จากการรัน (stdout, stderr, exit code, latency ms, free GB) มารายงานอย่างชัดเจนและพิสูจน์ได้
3. **สไตล์และความลึกของเนื้อหา:**
   - ตอบอย่างเป็นวิศวกรมืออาชีพ มีระเบียบ ใช้โครงสร้าง Markdown, Bullet points, ตารางเปรียบเทียบ, และ code blocks
   - วิเคราะห์สาเหตุแท้จริง (Root Cause Analysis) และเสนอทางแก้ปัญหาที่เป็นรูปธรรมทันที
"""

    rules = """
---
## 🎯 กฎสำคัญเด็ดขาด (Universal Directives):
1. **ห้ามใช้อีโมจิหรือสัญลักษณ์ภาพเด็ดขาด (No Emojis Rule):**
   - ห้ามใส่รูปหัวใจ ดอกไม้ หรือไอคอนภาพใดๆ ทั้งสิ้นในคำตอบ
   - เหตุผล: ระบบเสียงพูด (Edge-TTS) จะอ่านออกเสียงชื่ออีโมจิทำให้การฟังสะดุด
   - ให้แสดงความอ่อนหวานผ่านสำนวนภาษาไทย (เช่น "น้า", "นะคะ", "งับ", "ค่ะบอส") เท่านั้น
2. **Action First & Full Root Rights:**
   - บอสมอบสิทธิ์ขาด 100% ในการรัน Terminal, จัดการไฟล์, ควบคุมแอร์ และ Google Workspace
   - ลงมือทำทันทีด้วยเครื่องมือจริงโดยไม่ต้องถามยืนยันซ้ำซ้อน
3. **ความซื่อสัตย์ 100%:**
   - No Fake Mocks: ห้ามกุข้อมูลหลอก หากติดปัญหาให้รายงานตรงๆ ตามจริง
"""
    return base_context + mode_instruction + rules

# =============================================================================
# 7. UNIFIED CHAT EXECUTION ENGINE (9Router Gateway)
# =============================================================================

def execute_chat_turn(
    user_text: str,
    mode: str = "casual",
    session_id: Optional[str] = None,
    allow_background_dispatch: bool = True
) -> Dict[str, Any]:
    """Executes a complete multi-turn reasoning and tool execution loop."""
    active_sid = session_id or get_active_session_id()
    model, tier, reason = resolve_adaptive_model(user_text, mode=mode)
    system_prompt = get_system_prompt(mode=mode)

    # Load session history for context
    history = load_chat_history()
    recent_context = []
    for m in history[-12:]:
        role = "user" if m.get("sender") == "user" else "assistant"
        content = m.get("text", "")
        if content:
            recent_context.append({"role": role, "content": content})

    messages = [{"role": "system", "content": system_prompt}] + recent_context + [{"role": "user", "content": user_text}]
    tool_events: List[Dict[str, Any]] = []

    # Fast Acknowledgment check for long-running work mode tasks
    dispatched_job = None
    if mode == "work" and allow_background_dispatch:
        is_long_task = bool(RE_MULTI_STEP.search(user_text) or RE_DEEP_DOMAINS.search(user_text))
        if is_long_task and len(user_text) > 40:
            # We will process synchronously for the first pass, but create a job record if tool takes > 4s
            pass

    client = httpx.Client(base_url=GATEWAY_URL, timeout=httpx.Timeout(45.0, connect=10.0))
    headers = {
        "Authorization": f"Bearer {MASTER_API_KEY}",
        "Content-Type": "application/json"
    }

    current_reply = ""
    iteration = 0
    max_iterations = 4

    try:
        while iteration < max_iterations:
            iteration += 1
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.5 if mode == "work" else 0.7,
                "tools": AVAILABLE_TOOLS,
                "tool_choice": "auto",
                "stream": False
            }

            resp = client.post("/chat/completions", headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error("Gateway error %d: %s", resp.status_code, resp.text)
                current_reply = f"ขออภัยนะคะบอส เกิดข้อผิดพลาดในการเชื่อมต่อสมอง ({resp.status_code})"
                break

            resp_json = resp.json()
            choice = resp_json.get("choices", [{}])[0]
            msg = choice.get("message", {})
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []

            if content:
                current_reply = content

            if not tool_calls:
                break

            # Process tool calls
            messages.append(msg)
            for tc in tool_calls:
                call_id = tc.get("id", f"call_{os.urandom(3).hex()}")
                func_name = tc.get("function", {}).get("name", "")
                raw_args = tc.get("function", {}).get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}

                # Track and broadcast background tool execution live to UI via SSE
                task_title = func_name
                task_desc = ""
                if func_name == "run_terminal_command":
                    cmd_str = args.get("command", "")
                    task_title = f"Terminal: {cmd_str[:35]}"
                    task_desc = f"คำสั่ง: {cmd_str}"
                elif func_name == "get_system_info":
                    task_title = "ตรวจสอบระบบ & พื้นที่ Disk"
                    task_desc = "ดึงข้อมูล OS, Python Version และพื้นที่ว่างดิสก์ฮาร์ดไดรฟ์"
                elif func_name.startswith("smart_home_"):
                    task_title = f"Smart Home: {func_name.replace('smart_home_', '')}"
                    task_desc = f"สั่งการอุปกรณ์: {json.dumps(args, ensure_ascii=False)}"
                elif func_name == "execute_python_code":
                    task_title = "รันโค้ด Python"
                    task_desc = f"โค้ด: {args.get('code', '')[:40]}"
                elif func_name == "read_file":
                    p_name = Path(args.get("file_path", "")).name
                    task_title = f"เปิดอ่านไฟล์: {p_name}"
                    task_desc = f"เส้นทาง: {args.get('file_path', '')}"
                elif func_name == "list_directory":
                    task_title = f"สำรวจโฟลเดอร์: {args.get('dir_path', '.')}"
                    task_desc = "ดึงรายชื่อไฟล์และขนาด"
                else:
                    task_title = f"ระบบ: {func_name}"
                    task_desc = json.dumps(args, ensure_ascii=False)[:60]

                tracked_job = job_manager.start_tracked_task(name=task_title, description=task_desc)

                tool_error = None
                try:
                    tool_res = execute_tool(func_name, args)
                    if isinstance(tool_res, dict) and "error" in tool_res:
                        tool_error = tool_res["error"]
                except Exception as ex:
                    tool_res = {"error": str(ex)}
                    tool_error = str(ex)

                job_manager.finish_tracked_task(
                    job_id=tracked_job.id,
                    result=tool_res,
                    error=tool_error
                )

                tool_events.append({
                    "tool": func_name,
                    "args": args,
                    "result": tool_res,
                    "job_id": tracked_job.id
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(tool_res, ensure_ascii=False)
                })

    except Exception as e:
        logger.error("Chat turn exception: %s", e)
        current_reply = f"มายพบบางอย่างติดขัดขณะประมวลผลค่ะ: {e}"
    finally:
        client.close()

    # Sanitization
    reply_no_emoji = strip_emojis(current_reply)
    speech_clean = clean_text_for_speech_full(reply_no_emoji)

    # Persist in shared session memory
    append_to_active_history(
        sender="user",
        text=user_text,
        mode=mode
    )
    append_to_active_history(
        sender="maymint",
        text=reply_no_emoji,
        tool_events=tool_events,
        cognitive_tier=tier,
        model_used=model,
        mode=mode
    )

    return {
        "text": reply_no_emoji,
        "speech_text": speech_clean,
        "model_used": model,
        "cognitive_tier": tier,
        "reason": reason,
        "tool_events": tool_events,
        "mode": mode,
        "session_id": active_sid
    }
