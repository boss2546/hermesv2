#!/usr/bin/env python3
"""Maymint LiveKit Realtime Voice Agent Daemon (High-Fidelity Unified Edition).

Features:
- Native Direct Streaming Edge-TTS (No buffer underruns, zero latency, ultra-smooth Thai voice)
- Silero VAD with echo-bleed protection
- Maymint9RouterSTT: 9Router Multimodal Gemini Speech-to-Text with live room data broadcasting
- Real-time synchronization with Maymint Central Brain (memory/sessions/modes)
- Push-to-talk & Instant Manual Interruption (tap mic to cut off speech instantly)
- Dual Mode support (Casual 💬 / Work 🧠)
- Full 13 Hermes Tools Integration (Tuya AC, PowerShell, Google Workspace)
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import sys
import wave
from pathlib import Path
from typing import Optional

# Add project root and plugins to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
PLUGINS_DIR = PROJECT_ROOT / "hermes-agent" / "plugins"
if PLUGINS_DIR.exists():
    sys.path.insert(0, str(PLUGINS_DIR))
VOICE_PLUGIN_DIR = PLUGINS_DIR / "realtime_voice"
if VOICE_PLUGIN_DIR.exists():
    sys.path.insert(0, str(VOICE_PLUGIN_DIR))

# Import Maymint Brain
try:
    import maymint_brain
except Exception as e:
    logging.warning("Could not import maymint_brain: %s", e)
    maymint_brain = None

# Logging setup: console AND agent_daemon.log
LOG_FILE = Path(__file__).resolve().parent / "agent_daemon.log"
file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])
logger = logging.getLogger("maymint-daemon")

import edge_tts
import httpx
import openai as openai_sdk
from livekit import api, rtc
from livekit.agents import AgentSession, function_tool, stt, tts, voice
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions
from livekit.agents.utils import audio
from livekit.agents.voice import room_io
from livekit.plugins import openai, silero

try:
    from voice_engine import engine as voice_engine_inst  # type: ignore
except Exception as e:
    logger.warning("Could not import voice_engine directly: %s", e)
    voice_engine_inst = None

# Credentials from maymint_brain or environment
if maymint_brain and hasattr(maymint_brain, "ENV_VARS"):
    ENV_VARS = maymint_brain.ENV_VARS
else:
    ENV_VARS = {}

LIVEKIT_URL = ENV_VARS.get("LIVEKIT_URL", "ws://127.0.0.1:7880")
LIVEKIT_API_URL = "http://127.0.0.1:7880"
API_KEY = ENV_VARS.get("LIVEKIT_API_KEY", "maymint_key_bcf1fe4a923e6181")
API_SECRET = ENV_VARS.get("LIVEKIT_API_SECRET", "maymint_sec_0d4cedaee574e28e5d5cf90fb8c81e4c")
GATEWAY_URL = ENV_VARS.get("OPENAI_BASE_URL", "https://api.meuu.club/v1")
MASTER_API_KEY = ENV_VARS.get("OPENAI_API_KEY", "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c")
DEFAULT_VOICE = "th-TH-PremwadeeNeural"

# =========================================================================
# 1. DIRECT STREAMING EDGE-TTS PROVIDER
# =========================================================================
class MaymintEdgeTTSStream(tts.ChunkedStream):
    """Direct websocket streaming from Microsoft Edge-TTS into LiveKit WebRTC."""

    def __init__(
        self,
        tts_inst: tts.TTS,
        text: str,
        voice_name: str = DEFAULT_VOICE,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ):
        opts = conn_options if conn_options is not None else DEFAULT_API_CONNECT_OPTIONS
        super().__init__(tts=tts_inst, input_text=text, conn_options=opts)
        self.voice_name = voice_name

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        raw_text = self.input_text.strip()
        if not raw_text:
            return

        # Upfront sanitization for Thai pronunciation & Edge-TTS stability (No-Emoji rule)
        clean_text = re.sub(r"[\*#_~`]", "", raw_text)
        clean_text = re.sub(r"\s+ๆ", "ๆ", clean_text)
        if maymint_brain:
            clean_text = maymint_brain.clean_text_for_speech_full(clean_text)
        clean_text = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s.,?!%°C\-+]", "", clean_text)
        if not clean_text:
            return

        request_id = f"edge-{os.urandom(4).hex()}"
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=24000,
            num_channels=1,
            mime_type="audio/mp3",
        )

        chunk_count = 0
        total_bytes = 0
        t0 = asyncio.get_event_loop().time()

        for attempt in range(1, 4):
            try:
                tts_text = clean_text
                if attempt == 2:
                    tts_text = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s.,!?-]", " ", tts_text).strip()
                elif attempt >= 3 and voice_engine_inst is not None:
                    loop = asyncio.get_running_loop()
                    import tempfile
                    out_path = Path(tempfile.gettempdir()) / f"fallback_{os.urandom(4).hex()}.mp3"
                    await loop.run_in_executor(None, voice_engine_inst._synthesize_via_gateway, tts_text, self.voice_name, out_path)
                    if out_path.exists() and out_path.stat().st_size > 500:
                        fb_data = out_path.read_bytes()
                        output_emitter.push(fb_data)
                        chunk_count += 1
                        total_bytes += len(fb_data)
                        out_path.unlink(missing_ok=True)
                        break

                comm = edge_tts.Communicate(tts_text, self.voice_name)
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        data = chunk["data"]
                        output_emitter.push(data)
                        chunk_count += 1
                        total_bytes += len(data)

                if chunk_count > 0:
                    break
            except Exception as e:
                logger.warning("Direct Edge-TTS attempt %d warning: %s", attempt, e)
                if attempt < 3:
                    await asyncio.sleep(0.15 * attempt)

        output_emitter.flush()
        dur = asyncio.get_event_loop().time() - t0
        logger.info("✨ Direct EdgeTTS streamed %d chunks (%d bytes, took %.2fs) for: '%s'", chunk_count, total_bytes, dur, clean_text[:40])

class MaymintDirectEdgeTTS(tts.TTS):
    """Zero-latency continuous streaming TTS for Maymint."""

    def __init__(self, voice_name: str = DEFAULT_VOICE):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=24000,
            num_channels=1,
        )
        self.voice_name = voice_name

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> tts.ChunkedStream:
        return MaymintEdgeTTSStream(self, text, self.voice_name, conn_options=conn_options)

# =========================================================================
# 2. GEMINI TURN ORDER SANITIZER TRANSPORT
# =========================================================================
class GeminiTurnSanitizingTransport(httpx.AsyncBaseTransport):
    """Ensures Gemini turn alternation rules are met."""
    def __init__(self, transport: httpx.AsyncBaseTransport):
        self._transport = transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/chat/completions"):
            try:
                body_bytes = await request.aread()
                if body_bytes:
                    body = json.loads(body_bytes.decode("utf-8"))
                    msgs = body.get("messages", [])
                    if msgs and msgs[-1].get("role") == "assistant":
                        logger.info("🛡️ Sanitizing request: Trailing assistant turn detected -> Appending user prompt for Gemini")
                        msgs.append({"role": "user", "content": "ค่ะ ได้ยินมายชัดเจนไหมคะ"})
                        body["messages"] = msgs
                        new_content = json.dumps(body).encode("utf-8")
                        headers = dict(request.headers)
                        headers["content-length"] = str(len(new_content))
                        request = httpx.Request(
                            method=request.method,
                            url=request.url,
                            headers=headers,
                            content=new_content,
                            extensions=request.extensions
                        )
            except Exception as e:
                logger.warning("Sanitize transport warning: %s", e)

        return await self._transport.handle_async_request(request)

base_transport = httpx.AsyncHTTPTransport()
sanitized_transport = GeminiTurnSanitizingTransport(base_transport)
custom_http_client = httpx.AsyncClient(
    transport=sanitized_transport,
    timeout=httpx.Timeout(35.0, connect=10.0),
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MaymintLiveKit/2.0",
    }
)
openai_client = openai_sdk.AsyncClient(
    base_url=GATEWAY_URL,
    api_key=MASTER_API_KEY,
    http_client=custom_http_client
)

# =========================================================================
# 3. 9ROUTER NATIVE SPEECH-TO-TEXT (STT) ADAPTER WITH ROOM BROADCAST
# =========================================================================
class Maymint9RouterSTT(stt.STT):
    """Converts participant WebRTC speech frames into Thai text using 9Router Gemini."""

    def __init__(self, room_ref: Optional[rtc.Room] = None, on_transcript_cb=None):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,
                interim_results=False,
            )
        )
        self.room_ref = room_ref
        self.on_transcript_cb = on_transcript_cb

    async def _recognize_impl(
        self,
        buffer: audio.AudioBuffer,
        *,
        language: str | None = None,
        conn_options=None
    ) -> stt.SpeechEvent:
        try:
            merged = audio.merge_frames(buffer)
            raw_pcm = bytes(merged.data)
            if not raw_pcm or len(raw_pcm) < 2400:
                return stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[]
                )

            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(merged.num_channels)
                wf.setsampwidth(2)
                wf.setframerate(merged.sample_rate)
                wf.writeframes(raw_pcm)
            wav_bytes = buf.getvalue()

            logger.info("🎙️ Transcribing audio chunk (%d bytes, %dHz)...", len(wav_bytes), merged.sample_rate)
            t0 = asyncio.get_event_loop().time()

            loop = asyncio.get_running_loop()
            if voice_engine_inst is not None:
                transcript = await loop.run_in_executor(None, voice_engine_inst.transcribe_audio, wav_bytes)
            else:
                transcript = ""

            dur = asyncio.get_event_loop().time() - t0
            cleaned_text = transcript.strip().replace("", "")
            logger.info("📝 Transcribed text: '%s' (took %.2fs)", cleaned_text, dur)

            if not cleaned_text:
                return stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[]
                )

            # Broadcast transcribed speech to Web UI room via DataChannel
            if self.on_transcript_cb:
                try:
                    self.on_transcript_cb(cleaned_text)
                except Exception as cb_err:
                    logger.debug("Transcript callback warning: %s", cb_err)

            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[stt.SpeechData(language="th", text=cleaned_text)]
            )
        except Exception as e:
            logger.error("STT recognize error: %s", e)
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[]
            )

# Import Hermes Tools
try:
    from hermes_tools import HERMES_ALL_TOOLS
except ImportError:
    try:
        from gateway.livekit.hermes_tools import HERMES_ALL_TOOLS
    except ImportError:
        HERMES_ALL_TOOLS = []

active_sessions: dict[str, asyncio.Task] = {}

async def run_room_session(room_name: str):
    logger.info("🚀 Launching Maymint Voice Agent session for room: %s", room_name)
    token = (
        api.AccessToken(API_KEY, API_SECRET)
        .with_identity("maymint-agent")
        .with_name("Maymint (มายมิ้นท์)")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
                can_update_own_metadata=True
            )
        )
        .to_jwt()
    )

    room = rtc.Room()
    session: AgentSession | None = None
    current_mode = "casual"

    def broadcast_data(payload: dict):
        if room.isconnected():
            try:
                raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                asyncio.create_task(room.local_participant.publish_data(raw))
            except Exception as pe:
                logger.debug("Data publish warning: %s", pe)

    def on_user_transcript(text: str):
        logger.info("📢 Boss spoken text in room: '%s'", text)
        broadcast_data({
            "type": "transcript",
            "sender": "user",
            "text": text,
            "mode": current_mode
        })
        if maymint_brain:
            maymint_brain.append_to_active_history(
                sender="user",
                text=text,
                mode=current_mode
            )

    try:
        await room.connect(LIVEKIT_URL, token)
        logger.info("🟢 Connected to room %s! Active participants: %s", room_name, [p.identity for p in room.remote_participants.values()])

        vad_inst = silero.VAD.load(
            min_speech_duration=0.1,
            min_silence_duration=0.55,
            sample_rate=16000,
            force_cpu=True,
        )
        direct_tts = MaymintDirectEdgeTTS(DEFAULT_VOICE)
        stt_inst = Maymint9RouterSTT(room_ref=room, on_transcript_cb=on_user_transcript)

        # Build instructions using Maymint Brain
        system_instructions = maymint_brain.get_system_prompt(mode=current_mode) if maymint_brain else "คุณคือมายมิ้นท์ เลขาและแฟนสาวคู่คิดประจำตัวบอส"

        agent = voice.Agent(
            instructions=system_instructions,
            vad=vad_inst,
            stt=stt_inst,
            tts=direct_tts,
            llm=openai.LLM(
                client=openai_client,
                model=FAST_TIER_MODEL
            ),
            allow_interruptions=False,
            min_endpointing_delay=1.2,
            max_endpointing_delay=5.0,
            tools=HERMES_ALL_TOOLS,
        )

        # DataChannel Handler (Handles Mode Change, Instant Interrupt, and Speech synthesis requests)
        @room.on("data_received")
        def on_data_received(data_packet: rtc.DataPacket):
            nonlocal current_mode
            try:
                payload = json.loads(data_packet.data.decode("utf-8"))
                p_type = payload.get("type")

                if p_type == "mode_change":
                    new_mode = payload.get("mode", "casual")
                    if new_mode in ["casual", "work"]:
                        current_mode = new_mode
                        logger.info("🔄 Mode switched to '%s' in room %s", current_mode, room_name)
                        if maymint_brain:
                            new_inst = maymint_brain.get_system_prompt(mode=current_mode)
                            agent.update_instructions(new_inst)
                        broadcast_data({"type": "mode_ack", "mode": current_mode})

                elif p_type == "interrupt":
                    logger.info("✋ Instant manual interrupt requested by user in room %s", room_name)
                    if session is not None:
                        asyncio.create_task(session.interrupt(force=True))

                elif p_type == "speak":
                    text = payload.get("text", "").strip()
                    if text and session is not None:
                        logger.info("🗣️ Web UI requested agent speak: '%s'", text[:50])
                        asyncio.create_task(session.say(text))

            except Exception as e:
                logger.warning("Data packet processing warning: %s", e)

        async def on_user_text_input(sess: AgentSession, ev: room_io.TextInputEvent):
            logger.info("💬 Received user chat text message: '%s'", ev.text)
            try:
                async with sess._claim_user_turn():
                    try:
                        await sess.interrupt(force=True)
                    except Exception:
                        pass
                    sess.generate_reply(user_input=ev.text)
            except Exception as te:
                logger.error("Chat reply error: %s", te)

        room_opts = room_io.RoomOptions(
            text_input=room_io.TextInputOptions(text_input_cb=on_user_text_input)
        )
        session = AgentSession()

        # Listen to agent speech output events
        @session.on("agent_speech_committed")
        def on_agent_speech(speech_ev):
            text = getattr(speech_ev, "content", "") or getattr(speech_ev, "text", "")
            if text:
                logger.info("🌸 Maymint spoken: '%s'", text[:60])
                broadcast_data({
                    "type": "transcript",
                    "sender": "maymint",
                    "text": text,
                    "mode": current_mode
                })
                if maymint_brain:
                    maymint_brain.append_to_active_history(
                        sender="maymint",
                        text=text,
                        mode=current_mode
                    )

        await session.start(room=room, agent=agent, room_options=room_opts)
        logger.info("✨ Maymint AgentSession active in room %s (Unified Brain & Interruption Ready)", room_name)

        # Warm Greeting to Boss
        try:
            greeting = "สวัสดีค่ะบอส น้องมายมิ้นท์เชื่อมต่อสายสดแล้วค่ะ ได้ยินเสียงมายชัดเจนไหมคะ"
            await session.say(greeting)
            broadcast_data({
                "type": "transcript",
                "sender": "maymint",
                "text": greeting,
                "mode": current_mode
            })
            if maymint_brain:
                maymint_brain.append_to_active_history(
                    sender="maymint",
                    text=greeting,
                    mode=current_mode
                )
            logger.info("🔊 Greeting spoken in room %s", room_name)
        except Exception as e:
            logger.warning("Greeting warning in %s: %s", room_name, e)

        # Stay in room as long as human participants are connected
        while len(room.remote_participants) > 0:
            await asyncio.sleep(2)

        logger.info("👋 All participants left room %s. Closing session.", room_name)
    except asyncio.CancelledError:
        logger.info("Session cancelled for room %s", room_name)
    except Exception as e:
        logger.error("Error in room session %s: %s", room_name, e, exc_info=True)
    finally:
        if session is not None:
            try:
                await session.aclose()
            except Exception as se:
                logger.debug("Session aclose error: %s", se)
        try:
            await room.disconnect()
        except Exception:
            pass
        logger.info("Disconnected from room %s", room_name)

async def room_supervisor():
    logger.info("🌟 Starting Maymint Room Supervisor daemon with Unified Brain & Instant Interruption...")
    lk_api = api.LiveKitAPI(LIVEKIT_API_URL, API_KEY, API_SECRET)
    
    try:
        while True:
            try:
                res = await lk_api.room.list_rooms(api.ListRoomsRequest())
                for r in res.rooms:
                    p_res = await lk_api.room.list_participants(api.ListParticipantsRequest(room=r.name))
                    human_participants = [p for p in p_res.participants if p.identity != "maymint-agent"]
                    has_agent = any(p.identity == "maymint-agent" for p in p_res.participants)

                    if human_participants and not has_agent and r.name not in active_sessions:
                        logger.info("🎯 Detected room '%s' with %d participant(s). Spawning Maymint...", r.name, len(human_participants))
                        task = asyncio.create_task(run_room_session(r.name))
                        active_sessions[r.name] = task

                        def _cleanup(fut, name=r.name):
                            active_sessions.pop(name, None)
                        task.add_done_callback(_cleanup)

                for name, task in list(active_sessions.items()):
                    if task.done():
                        active_sessions.pop(name, None)

            except Exception as e:
                logger.error("Supervisor loop error: %s", e)

            await asyncio.sleep(2)
    finally:
        await lk_api.aclose()
        await custom_http_client.aclose()

if __name__ == "__main__":
    try:
        asyncio.run(room_supervisor())
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user.")
