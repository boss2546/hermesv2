"""Tool schemas and handlers for the realtime-voice plugin."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Tuple

from .voice_engine import VOICE_PRESETS, engine

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# 1. voice_speak Tool Schema
# ------------------------------------------------------------------------------
VOICE_SPEAK_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "voice_speak",
        "description": "Speak text out loud in real-time through the host speakers using natural Thai Microsoft Edge-TTS (th-TH-PremwadeeNeural).",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to speak out loud in Thai."
                },
                "voice": {
                    "type": "string",
                    "description": "Voice identifier or preset. Default is 'th-TH-PremwadeeNeural' (เสียงมายมิ้นท์).",
                    "default": "th-TH-PremwadeeNeural"
                },
                "play_async": {
                    "type": "boolean",
                    "description": "If true, play audio in background without blocking tool response. Default is false.",
                    "default": False
                }
            },
            "required": ["text"]
        }
    }
}


# ------------------------------------------------------------------------------
# 2. voice_transcribe Tool Schema (STT)
# ------------------------------------------------------------------------------
VOICE_TRANSCRIBE_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "voice_transcribe",
        "description": "Transcribe speech audio into Thai text using 9Router Multimodal Gemini 3.8 Flash High STT.",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path to the audio file (.mp3, .wav, .m4a) to transcribe."
                }
            },
            "required": ["audio_path"]
        }
    }
}


# ------------------------------------------------------------------------------
# 3. voice_status Tool Schema
# ------------------------------------------------------------------------------
VOICE_STATUS_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "voice_status",
        "description": "Check the status of the Real-time Voice Engine, current active voice, and available presets.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}


# ------------------------------------------------------------------------------
# 4. Check Function
# ------------------------------------------------------------------------------
def check_voice_available() -> Tuple[bool, Optional[str]]:
    """Verify prerequisites before dispatching voice tools."""
    return True, None


# ------------------------------------------------------------------------------
# 5. Handlers
# ------------------------------------------------------------------------------
def handle_voice_speak(args: Dict[str, Any], task_id: Optional[str] = None) -> str:
    """Handle voice_speak execution."""
    text = str(args.get("text", "")).strip()
    voice = args.get("voice", "th-TH-PremwadeeNeural")
    play_async = bool(args.get("play_async", False))

    if not text:
        return json.dumps({
            "success": False,
            "error": "The 'text' parameter cannot be empty."
        }, ensure_ascii=False)

    try:
        audio_file = engine.speak(text=text, voice=voice, block=not play_async)
        result = {
            "success": True,
            "spoken_text": text,
            "voice": engine.active_voice,
            "audio_file": str(audio_file),
            "status": "spoken_successfully"
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.exception("Failed in voice_speak: %s", exc)
        return json.dumps({
            "success": False,
            "error": f"Voice synthesis error: {exc}"
        }, ensure_ascii=False)


def handle_voice_transcribe(args: Dict[str, Any], task_id: Optional[str] = None) -> str:
    """Handle voice_transcribe execution."""
    audio_path = str(args.get("audio_path", "")).strip()
    if not audio_path:
        return json.dumps({
            "success": False,
            "error": "The 'audio_path' parameter is required."
        }, ensure_ascii=False)

    try:
        transcript = engine.transcribe_audio(audio_path)
        return json.dumps({
            "success": True,
            "audio_path": audio_path,
            "transcript": transcript
        }, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.exception("Failed in voice_transcribe: %s", exc)
        return json.dumps({
            "success": False,
            "error": f"Transcription error: {exc}"
        }, ensure_ascii=False)


def handle_voice_status(args: Dict[str, Any], task_id: Optional[str] = None) -> str:
    """Handle voice_status execution."""
    status = engine.get_status()
    result = {
        "success": True,
        "engine_tts": status["engine_tts"],
        "engine_stt": status["engine_stt"],
        "active_voice": status["active_voice"],
        "auto_speak_enabled": status["auto_speak"],
        "available_presets": list(VOICE_PRESETS.keys()),
        "gateway_url": status["gateway_url"]
    }
    return json.dumps(result, indent=2, ensure_ascii=False)
