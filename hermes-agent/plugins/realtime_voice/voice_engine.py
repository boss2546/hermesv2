"""Real-time voice synthesis (TTS) and transcription (STT) engine for Hermes Agent.

Powered by:
- TTS: Microsoft Edge-TTS Studio Neural Voice (th-TH-PremwadeeNeural)
- STT: 9Router Multimodal AI Gateway (https://api.meuu.club/v1) with ag/gemini-3.8-flash-high
- Playback: Cross-platform native audio player (afplay on macOS)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import platform
import re
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from .knowledge_lexicon import lexicon_mgr
except ImportError:
    try:
        from knowledge_lexicon import lexicon_mgr
    except ImportError:
        lexicon_mgr = None

logger = logging.getLogger(__name__)

# Constants
DEFAULT_VOICE = "th-TH-PremwadeeNeural"
DEFAULT_GATEWAY_URL = "https://api.meuu.club/v1"
DEFAULT_MASTER_KEY = "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"
DEFAULT_STT_MODEL = "ag/gemini-3.8-flash-high"

VOICE_PRESETS: Dict[str, str] = {
    "premwadee": "th-TH-PremwadeeNeural",
    "female-th": "th-TH-PremwadeeNeural",
    "maymint": "th-TH-PremwadeeNeural",
    "niwat": "th-TH-NiwatNeural",
    "male-th": "th-TH-NiwatNeural",
    "jenny": "en-US-JennyNeural",
    "guy": "en-US-GuyNeural",
}


def _resolve_api_key() -> str:
    """Retrieve the API key from environment or default master key."""
    return (
        os.getenv("MEUU_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or DEFAULT_MASTER_KEY
    )


class VoiceEngine:
    """Audio speech synthesis, transcription, and playback controller."""

    def __init__(self, default_voice: str = DEFAULT_VOICE):
        self.active_voice = default_voice
        self.auto_speak_enabled = False
        self.speed = "+0%"
        self.pitch = "+0Hz"
        self._lock = threading.Lock()
        self._temp_dir = Path(tempfile.gettempdir()) / "hermes_voice"
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    def set_voice(self, voice_name_or_preset: str) -> str:
        """Set the active voice using a preset or exact model identifier."""
        norm = voice_name_or_preset.strip().lower()
        if norm in VOICE_PRESETS:
            self.active_voice = VOICE_PRESETS[norm]
        else:
            self.active_voice = voice_name_or_preset.replace("edge-tts/", "")
        return self.active_voice

    def set_auto_speak(self, enabled: bool) -> bool:
        """Enable or disable auto-speaking responses."""
        with self._lock:
            self.auto_speak_enabled = enabled
            return self.auto_speak_enabled

    def get_status(self) -> Dict[str, Any]:
        """Return engine status and configuration."""
        return {
            "active_voice": self.active_voice,
            "auto_speak": self.auto_speak_enabled,
            "speed": self.speed,
            "pitch": self.pitch,
            "engine_tts": "Microsoft Edge-TTS (Studio 24kHz)",
            "engine_stt": f"9Router ({DEFAULT_STT_MODEL})",
            "gateway_url": DEFAULT_GATEWAY_URL,
        }

    # =========================================================================
    # 1. TEXT-TO-SPEECH (TTS) - Direct Microsoft Edge-TTS
    # =========================================================================

    def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[str] = None,
        pitch: Optional[str] = None,
        max_retries: int = 3,
    ) -> Path:
        """Synthesize Thai text into an MP3 file using Microsoft Edge-TTS with Auto-Retry."""
        clean_text = text.strip()
        clean_text = re.sub(r"\s+ๆ", "ๆ", clean_text)
        # Strip characters that cause Edge-TTS parser errors upfront (preserving Thai, English, digits, and basic punctuation)
        clean_text = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s.,!?-]", " ", clean_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if not clean_text:
            clean_text = "มายพร้อมดูแลบอสเสมอเลยค่ะ"


        selected_voice = voice or self.active_voice
        if selected_voice.lower() in VOICE_PRESETS:
            selected_voice = VOICE_PRESETS[selected_voice.lower()]
        else:
            selected_voice = selected_voice.replace("edge-tts/", "")

        rate_val = speed or self.speed
        pitch_val = pitch or self.pitch

        output_file = self._temp_dir / f"tts_{abs(hash(clean_text + selected_voice)) % 10000000}.mp3"

        # 1. Primary: High-speed, robust synthesis via 9Router Edge-TTS Gateway (~1-2s)
        try:
            return self._synthesize_via_gateway(clean_text, selected_voice, output_file)
        except Exception as gw_err:
            logger.warning("Gateway TTS synthesis failed (%s), attempting direct Edge-TTS...", gw_err)

        # 2. Fallback: Direct Edge-TTS synthesis via Async loop with progressive retries
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                if edge_tts is None:
                    raise ImportError("edge_tts package is not installed.")

                tts_text = clean_text
                if attempt == 2:
                    tts_text = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s.,!?-]", "", tts_text).strip()
                elif attempt >= 3:
                    # Simplify to concise sentence on final retry
                    parts = re.split(r"(ค่ะ|นะคะ|น้า|[\.!\n])", tts_text)
                    tts_text = "".join(parts[:2]).strip() if len(parts) >= 2 else "มายดูแลระบบให้เรียบร้อยแล้วนะคะบอส"
                    if len(tts_text) < 4:
                        tts_text = "มายพร้อมดูแลบอสเสมอเลยค่ะ"

                async def _run_edge():
                    comm = edge_tts.Communicate(
                        text=tts_text,
                        voice=selected_voice,
                        rate=rate_val,
                        pitch=pitch_val,
                    )
                    with open(output_file, "wb") as f:
                        async for chunk in comm.stream():
                            if chunk["type"] == "audio":
                                f.write(chunk["data"])

                asyncio.run(_run_edge())

                if output_file.exists() and output_file.stat().st_size > 500:
                    logger.info("Synthesized %s bytes using Direct Edge-TTS (Attempt %d)", output_file.stat().st_size, attempt)
                    return output_file

            except Exception as exc:
                last_error = exc
                logger.warning("Direct Edge-TTS attempt %d failed: %s", attempt, exc)
                time.sleep(0.3 * attempt)

        # Log failure and raise so caller handles
        logger.error("Edge-TTS failed after %d retries: %s", max_retries, last_error)
        raise RuntimeError(f"Edge-TTS synthesis failed: {last_error}")

    def _synthesize_via_gateway(self, text: str, voice: str, output_file: Path) -> Path:
        """High-performance synthesis via 9Router audio/speech endpoint."""
        api_key = _resolve_api_key()
        payload = {
            "model": f"edge-tts/{voice}",
            "input": text,
            "voice": f"edge-tts/{voice}",
        }
        req = urllib.request.Request(
            url=f"{DEFAULT_GATEWAY_URL}/audio/speech",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            audio_bytes = resp.read()
        output_file.write_bytes(audio_bytes)
        logger.info("Synthesized %s bytes via 9Router Edge-TTS Gateway", len(audio_bytes))
        return output_file

    # =========================================================================
    # 2. SPEECH-TO-TEXT (STT) - 9Router Multimodal Audio
    # =========================================================================

    def transcribe_audio(
        self,
        audio_source: Union[str, Path, bytes],
        prompt: Optional[str] = None,
        model: str = DEFAULT_STT_MODEL,
    ) -> str:
        """Transcribe an audio file into Thai text using 9Router Multimodal Model with Knowledge Lexicon."""
        if isinstance(audio_source, (str, Path)):
            audio_path = Path(audio_source)
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            audio_bytes = audio_path.read_bytes()
        else:
            audio_bytes = audio_source

        if len(audio_bytes) == 0:
            raise ValueError("Audio data is empty.")

        # If no explicit custom prompt provided, prime model with rich domain knowledge lexicon
        if prompt is None:
            if lexicon_mgr is not None:
                prompt = lexicon_mgr.generate_stt_system_prompt()
            else:
                prompt = "ฟังเสียงนี้แล้วถอดความภาษาไทยออกมา ตอบเฉพาะข้อความที่ได้ยินเท่านั้น ห้ามมีคำอธิบายเพิ่มเติม:"

        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_b64,
                                "format": "mp3",
                            },
                        },
                    ],
                }
            ],
            "temperature": 0.0,
            "stream": False,
        }

        api_key = _resolve_api_key()
        req = urllib.request.Request(
            url=f"{DEFAULT_GATEWAY_URL}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Hermes/1.0",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30.0) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

            # Handle both standard JSON and SSE response format
            text = ""
            if "text/event-stream" in resp.headers.get("Content-Type", ""):
                for line in raw.splitlines():
                    line = line.strip()
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                text += delta["content"]
                        except Exception:
                            pass
            else:
                data = json.loads(raw)
                text = data["choices"][0]["message"]["content"].strip()

        raw_transcript = text.strip()

        # Double-Shield: Apply Lexicon Normalization to eliminate any residual phonetic distortions
        if lexicon_mgr is not None:
            try:
                normalized, applied = lexicon_mgr.normalize_text(raw_transcript)
                if applied:
                    logger.info("STT Lexicon Normalizer corrected %d items: '%s' -> '%s'", len(applied), raw_transcript, normalized)
                return normalized
            except Exception as norm_err:
                logger.warning("Lexicon post-normalization error: %s", norm_err)

        return raw_transcript

    # =========================================================================
    # 3. PLAYBACK & IMMEDIATE SPEAK
    # =========================================================================

    def play_audio(self, audio_path: Path, block: bool = True) -> bool:
        """Play audio on the host system using native OS audio player."""
        if not audio_path.exists():
            logger.error("Audio file does not exist: %s", audio_path)
            return False

        sys_name = platform.system()

        def _run_player():
            try:
                if sys_name == "Darwin":  # macOS
                    subprocess.run(["afplay", str(audio_path)], check=True)
                elif sys_name == "Linux":
                    for player in [["paplay"], ["ffplay", "-nodisp", "-autoexit"], ["mpv", "--no-video"]]:
                        try:
                            subprocess.run([*player, str(audio_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            return
                        except Exception:
                            continue
                elif sys_name == "Windows":
                    cmd = f'(New-Object Media.SoundPlayer "{audio_path}").PlaySync();'
                    subprocess.run(["powershell", "-c", cmd], check=True)
            except Exception as e:
                logger.warning("Playback completed or interrupted: %s", e)

        if block:
            _run_player()
        else:
            thread = threading.Thread(target=_run_player, daemon=True, name="voice-playback")
            thread.start()

        return True

    def speak(self, text: str, voice: Optional[str] = None, block: bool = True) -> Path:
        """Synthesize text into speech and play it out loud."""
        audio_file = self.synthesize_speech(text, voice=voice)
        self.play_audio(audio_file, block=block)
        return audio_file


# Global singleton engine instance
engine = VoiceEngine()
