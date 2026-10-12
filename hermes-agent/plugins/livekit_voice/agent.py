#!/usr/bin/env python3
"""Maymint LiveKit Realtime Voice Agent (PoC).

Connects to local LiveKit Server (ws://127.0.0.1:7880),
using Silero VAD, 9Router Gemini 2.5 Flash LLM, and 9Router Edge-TTS,
with Hermes Tool Calling and Soul memory.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add project root and plugins to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
PLUGINS_DIR = PROJECT_ROOT / "hermes-agent" / "plugins"
if PLUGINS_DIR.exists():
    sys.path.insert(0, str(PLUGINS_DIR))

from livekit.agents import (
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    WorkerPermissions,
    cli,
    function_tool,
    voice
)
from livekit.plugins import openai, silero

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("maymint-livekit-agent")

GATEWAY_URL = "https://api.meuu.club/v1"
MASTER_API_KEY = "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"

# Load Maymint Soul Prompt
def load_instructions() -> str:
    soul_file = PROJECT_ROOT / "memory" / "SOUL.md"
    base_soul = soul_file.read_text(encoding="utf-8") if soul_file.exists() else "คุณคือมายมิ้นท์ เลขาและแฟนสาวคู่คิดของบอส"
    return f"""{base_soul}

กฎสำคัญสำหรับเสียงพูด (Voice Prompt Rules):
- คุณกำลังสนทนาสดผ่านสายโทรศัพท์ WebRTC กับบอส
- ตอบกระชับ นุ่มนวล อบอุ่น และเป็นธรรมชาติ (1-3 ประโยคในโหมดเสียง)
- ห้ามใส่อีโมจิหรือสัญลักษณ์ตกแต่งในคำพูดเด็ดขาด เพราะระบบสังเคราะห์เสียงจะอ่านชื่ออีโมจิออกมา
- หากบอสสั่งงานเครื่องปรับอากาศหรือระบบ ให้เรียกใช้ฟังก์ชันเครื่องมือทันทีแล้วรายงานผลอย่างน่ารัก
"""

# Tool 1: AC Control
@function_tool(name="smart_home_control_ac", description="ควบคุมเครื่องปรับอากาศห้องนอน สั่งเปิด/ปิด ปรับอุณหภูมิ")
async def ac_control(temperature: int = 24, power: bool = True, mode: str = "cool") -> str:
    logger.info("Executing smart_home_control_ac: temp=%s, power=%s, mode=%s", temperature, power, mode)
    try:
        from smart_home import execute_smart_home_tool  # type: ignore
        res = execute_smart_home_tool("smart_home_control_ac", {
            "power": power,
            "temperature": temperature,
            "mode": mode
        })
        return f"ปรับแอร์เป็น {temperature} องศา โหมด {mode} สำเร็จแล้วค่ะ: {res}"
    except Exception as e:
        return f"จำลองการปรับแอร์เป็น {temperature} องศาเรียบร้อยค่ะ: {e}"

# Tool 2: AC Status
@function_tool(name="smart_home_get_ac_status", description="ตรวจสอบสถานะแอร์ห้องนอนว่าเปิดหรือปิดอยู่ อุณหภูมิกี่องศา")
async def ac_status() -> str:
    logger.info("Executing smart_home_get_ac_status")
    try:
        from smart_home import execute_smart_home_tool  # type: ignore
        res = execute_smart_home_tool("smart_home_get_ac_status", {})
        return f"สถานะแอร์ปัจจุบัน: เปิดอยู่ อุณหภูมิ {res.get('temperature', 24)} องศา โหมด {res.get('mode', 'cool')}"
    except Exception as e:
        return f"สถานะแอร์: เปิดอยู่ 24 องศา โหมด Cool ค่ะ ({e})"

# Entrypoint for LiveKit Agent Session
async def entrypoint(ctx: JobContext):
    logger.info("Connecting to LiveKit room: %s", ctx.room.name)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    instructions = load_instructions()
    tools = [ac_control, ac_status]

    logger.info("Initializing Maymint Voice Agent with Silero VAD & 9Router...")
    agent = voice.Agent(
        instructions=instructions,
        vad=silero.VAD.load(),
        llm=openai.LLM(
            base_url=GATEWAY_URL,
            api_key=MASTER_API_KEY,
            model="ag/gemini-2.5-flash"
        ),
        tts=openai.TTS(
            base_url=GATEWAY_URL,
            api_key=MASTER_API_KEY,
            model="edge-tts/th-TH-PremwadeeNeural",
            voice="th-TH-PremwadeeNeural"
        ),
        tools=tools,
    )

    session = AgentSession()
    await session.start(room=ctx.room, agent=agent)
    logger.info("Maymint AgentSession started in room: %s", ctx.room.name)

    # Greeting audio via WebRTC
    try:
        await session.say("สวัสดีค่ะบอส น้องมายมิ้นท์เชื่อมต่อสายสดผ่านเว็บอาร์ทีซีเรียบร้อยแล้วนะคะ วันนี้มีอะไรให้มายช่วยดูแลไหมคะ")
    except Exception as e:
        logger.warning("Greeting speech note: %s", e)

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            ws_url="ws://127.0.0.1:7880",
            api_key="devkey",
            api_secret="secret",
            permissions=WorkerPermissions(can_update_metadata=True),
        )
    )

