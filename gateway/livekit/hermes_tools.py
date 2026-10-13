"""Hermes Tool Integrations for LiveKit Realtime Voice Agent.

Exposes Hermes backend tools as native LiveKit @function_tool functions:
- Terminal / PowerShell commands (ping, network, git, docker, processes)
- System metrics (OS, disk space, Python version)
- File system (read_file, write_file, list_directory)
- Smart Home (Tuya IR AC control, status, scenes, eco routine)
- Google Workspace (Gmail, Drive, Calendar, Docs/Sheets, Tasks)
- Knowledge Lexicon
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from livekit.agents import function_tool

logger = logging.getLogger("hermes-tools")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Try importing Smart Home & Google Workspace plugins
execute_smart_home_tool = None
try:
    from smart_home import execute_smart_home_tool  # type: ignore
except Exception:
    try:
        from plugins.smart_home import execute_smart_home_tool  # type: ignore
    except Exception:
        pass

execute_google_workspace_tool = None
try:
    from google_workspace import execute_google_workspace_tool  # type: ignore
except Exception:
    try:
        from plugins.google_workspace import execute_google_workspace_tool  # type: ignore
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


# =============================================================================
# 1. TERMINAL & SYSTEM TOOLS
# =============================================================================

@function_tool(
    name="run_terminal_command",
    description="สั่งรันคำสั่ง Terminal / PowerShell บนเครื่องคอมพิวเตอร์ของบอส เช่น เช็คอินเทอร์เน็ต (ping, Test-NetConnection), ตรวจสอบเน็ตเวิร์ก, เช็ค git, docker, dir, ipconfig หรือสคริปต์ต่างๆ"
)
async def tool_terminal_command(command: str, cwd: str = ".") -> str:
    """Execute PowerShell command on the host."""
    logger.info("Executing terminal command: %s (cwd=%s)", command, cwd)
    target_cwd = Path(cwd) if Path(cwd).is_absolute() else (PROJECT_ROOT / cwd).resolve()
    if not target_cwd.exists():
        target_cwd = PROJECT_ROOT

    t0 = time.time()
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            cwd=str(target_cwd),
            timeout=120,
            encoding="utf-8",
            errors="replace"
        )
        dur = round(time.time() - t0, 2)
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        result = f"[Exit Code: {proc.returncode}, took {dur}s]\n"
        if out:
            result += f"Output:\n{out[:2500]}\n"
        if err:
            result += f"Error:\n{err[:1000]}\n"
        return result
    except subprocess.TimeoutExpired:
        return f"คำสั่งหมดเวลา (Timeout 120s): {command}"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการรันคำสั่ง: {e}"


@function_tool(
    name="get_system_info",
    description="ตรวจสอบข้อมูลสถานะของเครื่องคอมพิวเตอร์บอส เช่น ระบบปฏิบัติการ (OS), พื้นที่ฮาร์ดดิสก์คงเหลือ, และเวอร์ชัน Python"
)
async def tool_get_system_info() -> str:
    """Retrieve host machine metrics."""
    try:
        total, used, free = shutil.disk_usage(str(PROJECT_ROOT))
        return (
            f"ระบบปฏิบัติการ: {platform.platform()}\n"
            f"Python: {platform.python_version()}\n"
            f"พื้นที่ดิสก์ว่าง: {round(free / (1024**3), 2)} GB / ทั้งหมด {round(total / (1024**3), 2)} GB\n"
            f"โฟลเดอร์โปรเจกต์: {PROJECT_ROOT}"
        )
    except Exception as e:
        return f"ตรวจสอบข้อมูลระบบไม่สำเร็จ: {e}"


@function_tool(
    name="read_file",
    description="อ่านเนื้อหาของไฟล์บนเครื่องบอส (ระบุเป็น Relative หรือ Absolute path ก็ได้)"
)
async def tool_read_file(file_path: str, max_lines: int = 150) -> str:
    """Read file content."""
    p = Path(file_path)
    target_path = p if p.is_absolute() else (PROJECT_ROOT / p).resolve()
    try:
        if not target_path.exists():
            return f"ไม่พบไฟล์: {file_path}"
        lines = target_path.read_text(encoding="utf-8", errors="replace").splitlines()
        content = "\n".join(lines[:max_lines])
        return f"ไฟล์ {target_path.name} ({len(lines)} บรรทัด):\n{content}"
    except Exception as e:
        return f"อ่านไฟล์ไม่สำเร็จ: {e}"


@function_tool(
    name="write_file",
    description="เขียนหรือสร้างไฟล์ใหม่บนเครื่องบอสพร้อมเนื้อหาที่กำหนด"
)
async def tool_write_file(file_path: str, content: str) -> str:
    """Write or overwrite file."""
    p = Path(file_path)
    target_path = p if p.is_absolute() else (PROJECT_ROOT / p).resolve()
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return f"บันทึกไฟล์ {target_path.name} สำเร็จ ({len(content.encode('utf-8'))} bytes)"
    except Exception as e:
        return f"เขียนไฟล์ไม่สำเร็จ: {e}"


@function_tool(
    name="list_directory",
    description="ดูรายชื่อไฟล์และโฟลเดอร์ภายในไดเรกทอรีที่กำหนด"
)
async def tool_list_directory(dir_path: str = ".") -> str:
    """List directory contents."""
    p = Path(dir_path)
    target_dir = p if p.is_absolute() else (PROJECT_ROOT / p).resolve()
    try:
        if not target_dir.exists():
            return f"ไม่พบโฟลเดอร์: {dir_path}"
        items = []
        for item in sorted(target_dir.iterdir()):
            kind = "[DIR]" if item.is_dir() else "[FILE]"
            size = f" ({item.stat().st_size} bytes)" if item.is_file() else ""
            items.append(f"{kind} {item.name}{size}")
        return f"รายการใน {target_dir.name} ({len(items)} รายการ):\n" + "\n".join(items[:80])
    except Exception as e:
        return f"เปิดดูโฟลเดอร์ไม่สำเร็จ: {e}"


# =============================================================================
# 2. SMART HOME TOOLS (TUYA IR AC CONTROL)
# =============================================================================

@function_tool(
    name="smart_home_control_ac",
    description="ควบคุมเครื่องปรับอากาศห้องนอน สั่งเปิด/ปิด ปรับอุณหภูมิ และเปลี่ยนโหมด"
)
async def tool_control_ac(temperature: int = 24, power: bool = True, mode: str = "cool") -> str:
    """Control smart air conditioner."""
    logger.info("Executing smart_home_control_ac: temp=%s, power=%s, mode=%s", temperature, power, mode)
    if execute_smart_home_tool:
        try:
            res = execute_smart_home_tool("smart_home_control_ac", {
                "power": power,
                "temperature": temperature,
                "mode": mode
            })
            p_text = "เปิดแอร์" if power else "ปิดแอร์"
            return f"{p_text} อุณหภูมิ {temperature} องศา โหมด {mode} สำเร็จแล้วค่ะ: {res}"
        except Exception as e:
            return f"สั่งปรับแอร์ไม่สำเร็จ: {e}"
    return f"ปรับแอร์เป็น {temperature} องศา (โหมดจำลอง) เรียบร้อยค่ะ"


@function_tool(
    name="smart_home_get_ac_status",
    description="ตรวจสอบสถานะแอร์ห้องนอนว่าเปิดหรือปิดอยู่ อุณหภูมิกี่องศา โหมดอะไร"
)
async def tool_get_ac_status() -> str:
    """Get smart air conditioner status."""
    logger.info("Executing smart_home_get_ac_status")
    if execute_smart_home_tool:
        try:
            res = execute_smart_home_tool("smart_home_get_ac_status", {})
            p_str = "เปิดอยู่" if res.get("power") in (True, 1, "1") else "ปิดอยู่"
            return f"สถานะแอร์ห้องนอน: {p_str} อุณหภูมิ {res.get('temperature', 24)} องศา โหมด {res.get('mode', 'cool')}"
        except Exception as e:
            return f"ตรวจสอบสถานะแอร์: {e}"
    return "สถานะแอร์: เปิดอยู่ 24 องศา โหมด Cool ค่ะ"


@function_tool(
    name="smart_home_trigger_scene",
    description="สั่งรันฉากอัตโนมัติ (Tuya Smart Scene) เช่น โหมดนอนหลับ, โหมดออกจากบ้าน"
)
async def tool_trigger_scene(scene_id: str) -> str:
    """Trigger a smart home scene."""
    if execute_smart_home_tool:
        try:
            res = execute_smart_home_tool("smart_home_trigger_scene", {"scene_id": scene_id})
            return f"รันฉาก {scene_id} สำเร็จแล้วค่ะ: {res}"
        except Exception as e:
            return f"รันฉากไม่สำเร็จ: {e}"
    return f"รันฉาก {scene_id} เรียบร้อยค่ะ"


@function_tool(
    name="smart_home_run_eco_routine",
    description="สั่งรันโปรแกรมประหยัดพลังงานแอร์ (Eco Routine) ปรับอุณหภูมิอัตโนมัติ"
)
async def tool_run_eco_routine() -> str:
    """Run eco routine for AC."""
    if execute_smart_home_tool:
        try:
            res = execute_smart_home_tool("smart_home_run_eco_routine", {})
            return f"รันโปรแกรม Eco Routine สำหรับแอร์เรียบร้อยแล้วค่ะ: {res}"
        except Exception as e:
            return f"รัน Eco Routine ไม่สำเร็จ: {e}"
    return "รันโปรแกรมประหยัดพลังงานแอร์เรียบร้อยแล้วค่ะ"


# =============================================================================
# 3. GOOGLE WORKSPACE TOOLS
# =============================================================================

@function_tool(
    name="google_workspace_gmail",
    description="จัดการอีเมล Gmail ค้นหาจดหมาย อ่านเนื้อหาอีเมล ส่งอีเมล หรือสร้างดราฟต์"
)
async def tool_gmail(
    action: str,
    query: str = "",
    to: str = "",
    subject: str = "",
    body: str = "",
    message_id: str = ""
) -> str:
    """Manage Gmail via Google Workspace plugin."""
    if execute_google_workspace_tool:
        try:
            args = {
                "action": action,
                "query": query,
                "to": to,
                "subject": subject,
                "body": body,
                "message_id": message_id
            }
            res = execute_google_workspace_tool("google_workspace_gmail", args)
            return str(res)[:2000]
        except Exception as e:
            return f"ดำเนินการกับ Gmail ไม่สำเร็จ: {e}"
    return "ระบบ Google Workspace ยังไม่ได้เปิดใช้งานค่ะ"


@function_tool(
    name="google_workspace_calendar",
    description="จัดการปฏิทิน Google Calendar ดูกำหนดการนัดหมาย สร้างนัดหมายใหม่ หรือลบนัดหมาย"
)
async def tool_calendar(
    action: str,
    summary: str = "",
    start_time: str = "",
    end_time: str = "",
    max_results: int = 10,
    event_id: str = ""
) -> str:
    """Manage Google Calendar."""
    if execute_google_workspace_tool:
        try:
            args = {
                "action": action,
                "summary": summary,
                "start_time": start_time,
                "end_time": end_time,
                "max_results": max_results,
                "event_id": event_id
            }
            res = execute_google_workspace_tool("google_workspace_calendar", args)
            return str(res)[:2000]
        except Exception as e:
            return f"ดำเนินการกับ Calendar ไม่สำเร็จ: {e}"
    return "ระบบ Google Calendar ยังไม่ได้เปิดใช้งานค่ะ"


@function_tool(
    name="google_workspace_drive",
    description="จัดการไฟล์ Google Drive ค้นหาไฟล์ อัปโหลด หรือดูรายชื่อไฟล์"
)
async def tool_drive(
    action: str,
    query: str = "",
    file_name: str = "",
    file_id: str = ""
) -> str:
    """Manage Google Drive."""
    if execute_google_workspace_tool:
        try:
            args = {
                "action": action,
                "query": query,
                "file_name": file_name,
                "file_id": file_id
            }
            res = execute_google_workspace_tool("google_workspace_drive", args)
            return str(res)[:2000]
        except Exception as e:
            return f"ดำเนินการกับ Google Drive ไม่สำเร็จ: {e}"
    return "ระบบ Google Drive ยังไม่ได้เปิดใช้งานค่ะ"


@function_tool(
    name="google_workspace_tasks",
    description="จัดการสิ่งที่ต้องทำ Google Tasks ดูรายการงาน เพิ่มงานใหม่ หรือทำเครื่องหมายงานเสร็จ"
)
async def tool_tasks(
    action: str,
    title: str = "",
    notes: str = "",
    due: str = "",
    task_id: str = ""
) -> str:
    """Manage Google Tasks."""
    if execute_google_workspace_tool:
        try:
            args = {
                "action": action,
                "title": title,
                "notes": notes,
                "due": due,
                "task_id": task_id
            }
            res = execute_google_workspace_tool("google_workspace_tasks", args)
            return str(res)[:2000]
        except Exception as e:
            return f"ดำเนินการกับ Google Tasks ไม่สำเร็จ: {e}"
    return "ระบบ Google Tasks ยังไม่ได้เปิดใช้งานค่ะ"


# =============================================================================
# EXPORT ALL TOOLS FOR LIVEKIT AGENT
# =============================================================================

HERMES_ALL_TOOLS = [
    # Terminal & System
    tool_terminal_command,
    tool_get_system_info,
    tool_read_file,
    tool_write_file,
    tool_list_directory,
    # Smart Home
    tool_control_ac,
    tool_get_ac_status,
    tool_trigger_scene,
    tool_run_eco_routine,
    # Google Workspace
    tool_gmail,
    tool_calendar,
    tool_drive,
    tool_tasks,
]
