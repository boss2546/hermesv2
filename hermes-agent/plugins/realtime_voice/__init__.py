"""Real-time Voice Chat plugin for Hermes Agent.

Provides:
- Slash commands: `/voice say <text>`, `/voice status`, `/voice set-voice <name>`, `/voice auto-speak <on/off>`
- Custom tools: `voice_speak`, `voice_transcribe`, `voice_status`
- Auto-speak hook for real-time speech responses
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from . import tools as _t
from .voice_engine import VOICE_PRESETS, engine

logger = logging.getLogger(__name__)


def _clean_text_for_speech(text: str) -> str:
    """Strip code blocks, URLs, and markdown formatting to speak naturally."""
    # Remove code blocks
    cleaned = re.sub(r"```[\s\S]*?```", " [เนื้อหาโค้ด] ", text)
    # Remove inline code
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    # Remove URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Remove markdown headers and list markers
    cleaned = re.sub(r"^[#*>\-\d.]+\s+", "", cleaned, flags=re.MULTILINE)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# ------------------------------------------------------------------------------
# 1. Lifecycle Hooks
# ------------------------------------------------------------------------------
def _on_session_start(session_id: str, **kwargs) -> None:
    """Invoked when a Hermes session begins."""
    logger.info("[realtime-voice] Session started with voice engine ready: %s", session_id)


def _on_session_end(session_id: str, **kwargs) -> None:
    """Invoked when a Hermes session ends."""
    logger.info("[realtime-voice] Session ended: %s", session_id)


def _on_post_llm_call(response_text: str, **kwargs) -> None:
    """Optionally auto-speak AI response if auto_speak is enabled."""
    if engine.auto_speak_enabled and response_text.strip():
        try:
            speech_text = _clean_text_for_speech(response_text)
            if speech_text:
                # Speak asynchronously in background so response stream isn't blocked
                engine.speak(speech_text[:500], block=False)
        except Exception as e:
            logger.debug("[realtime-voice] Auto-speak skipped: %s", e)


# ------------------------------------------------------------------------------
# 2. Slash Command Handler (/voice)
# ------------------------------------------------------------------------------
def _handle_voice_slash(raw_args: str) -> Optional[str]:
    """Slash command handler for /voice in chat or CLI."""
    argv = raw_args.strip().split()
    if not argv or argv[0] in {"help", "-h", "--help"}:
        return (
            "🎙️ **Real-time Voice Chat Commands:**\n"
            "  • `/voice say <text>`         — ให้มายมิ้นท์พูดประโยคที่ต้องการออกลำโพง\n"
            "  • `/voice status`             — เช็กสถานะเครื่องยนต์เสียงและการตั้งค่า\n"
            "  • `/voice set-voice <preset>` — สลับเสียง (premwadee, niwat, jenny, guy)\n"
            "  • `/voice auto-speak on|off`  — เปิด/ปิด การพูดตอบคำถามอัตโนมัติ"
        )

    subcmd = argv[0].lower()

    if subcmd == "status":
        status = engine.get_status()
        return (
            f"🎙️ **Realtime Voice Engine Status:**\n"
            f"  • **TTS Engine:** `{status['engine_tts']}`\n"
            f"  • **STT Engine:** `{status['engine_stt']}`\n"
            f"  • **Active Voice:** `{status['active_voice']}` (มายมิ้นท์ 💖)\n"
            f"  • **Auto-Speak:** `{'ON 🟢' if status['auto_speak'] else 'OFF ⚪'}`\n"
            f"  • **Available Presets:** {', '.join(VOICE_PRESETS.keys())}\n"
            f"  • **Gateway URL:** `{status['gateway_url']}`"
        )

    elif subcmd == "say":
        text = " ".join(argv[1:]).strip()
        if not text:
            return "❌ กรุณาระบุข้อความที่ต้องการให้พูด เช่น: `/voice say สวัสดีค่ะบอส`"
        try:
            engine.speak(text, block=False)
            return f"🔊 กำลังส่งเสียงพูด: \"{text}\" ✨"
        except Exception as err:
            return f"❌ เกิดข้อผิดพลาดในการสร้างเสียง: {err}"

    elif subcmd == "set-voice":
        if len(argv) < 2:
            return f"❌ กรุณาระบุชื่อเสียงที่ต้องการ Presets: {', '.join(VOICE_PRESETS.keys())}"
        target = argv[1]
        active = engine.set_voice(target)
        return f"✅ เปลี่ยนเสียงพูดเป็น: `{active}` เรียบร้อยแล้วค่ะบอส! 💖"

    elif subcmd in ("auto-speak", "autospeak"):
        if len(argv) < 2:
            return f"Auto-speak ตอนนี้เป็น {'ON 🟢' if engine.auto_speak_enabled else 'OFF ⚪'}. ใช้ `/voice auto-speak on` หรือ `/voice auto-speak off`"
        mode = argv[1].lower()
        if mode in ("on", "true", "1", "yes"):
            engine.set_auto_speak(True)
            return "🔊 เปิดโหมด **Auto-Speak (พูดเสียงตอบโต้อัตโนมัติ)** เรียบร้อยแล้วค่ะบอส! 💖"
        else:
            engine.set_auto_speak(False)
            return "🔇 ปิดโหมด **Auto-Speak** เรียบร้อยแล้วค่ะบอส!"

    else:
        return f"❓ คำสั่งไม่ถูกต้อง: '{subcmd}'. พิมพ์ `/voice help` เพื่อดูวิธีใช้งานค่ะ"


# ------------------------------------------------------------------------------
# 3. Registration
# ------------------------------------------------------------------------------
def register(ctx) -> None:
    """Register realtime-voice plugin into Hermes Agent."""
    # 1. Hooks
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_hook("post_llm_call", _on_post_llm_call)

    # 2. Slash command
    ctx.register_command(
        name="voice",
        handler=_handle_voice_slash,
        description="Real-time voice chat and neural speech synthesis."
    )

    # 3. Tools
    ctx.register_tool(
        name="voice_speak",
        toolset="voice",
        schema=_t.VOICE_SPEAK_SCHEMA,
        handler=_t.handle_voice_speak,
        check_fn=_t.check_voice_available,
        emoji="🎙️"
    )
    ctx.register_tool(
        name="voice_transcribe",
        toolset="voice",
        schema=_t.VOICE_TRANSCRIBE_SCHEMA,
        handler=_t.handle_voice_transcribe,
        check_fn=_t.check_voice_available,
        emoji="✍️"
    )
    ctx.register_tool(
        name="voice_status",
        toolset="voice",
        schema=_t.VOICE_STATUS_SCHEMA,
        handler=_t.handle_voice_status,
        check_fn=_t.check_voice_available,
        emoji="🔊"
    )
