#!/usr/bin/env python3
"""Maymint LiveKit Realtime Voice Agent Daemon (High-Fidelity Audio Edition).

Auto-dispatches Maymint into active rooms created on LiveKit Server (ws://127.0.0.1:7880).
Features:
- Native Direct Streaming Edge-TTS (No buffer underruns, zero latency, ultra-smooth Thai voice)
- Silero VAD with echo-bleed protection (allow_interruptions=False for flawless speech delivery)
- Maymint9RouterSTT (Multimodal 9Router Speech-to-Text with Knowledge Lexicon)
- 9Router Gemini 2.5 Flash LLM (ultra-fast reasoning & tool calling with turn safety)
- Hermes Tuya Smart Home AC Plugin
- Maymint Soul & Memory integration
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

# Add project root and plugins to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
PLUGINS_DIR = PROJECT_ROOT / "hermes-agent" / "plugins"
if PLUGINS_DIR.exists():
    sys.path.insert(0, str(PLUGINS_DIR))
VOICE_PLUGIN_DIR = PLUGINS_DIR / "realtime_voice"
if VOICE_PLUGIN_DIR.exists():
    sys.path.insert(0, str(VOICE_PLUGIN_DIR))

# Logging setup: write to console AND agent_daemon.log file
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

LIVEKIT_URL = "ws://127.0.0.1:7880"
LIVEKIT_API_URL = "http://127.0.0.1:7880"
API_KEY = "devkey"
API_SECRET = "secret"
GATEWAY_URL = "https://api.meuu.club/v1"
MASTER_API_KEY = "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"
DEFAULT_VOICE = "th-TH-PremwadeeNeural"

# =========================================================================
# 1. DIRECT STREAMING EDGE-TTS PROVIDER (PREVENTS AUDIO STUTTER / CHOPPINESS)
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

        # Upfront sanitization for Thai pronunciation & Edge-TTS stability
        clean_text = re.sub(r"[\*#_~`]", "", raw_text)
        clean_text = re.sub(r"\s+ๆ", "ๆ", clean_text)
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
                    # Fallback to 9Router Edge-TTS HTTP Gateway if direct websocket drops
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
    """Intercepts OpenAI completions and ensures Gemini alternation rules are met.
    
    Prevents: 400 Bad Request: 'Requests ending with a model turn are not supported.'
    """
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

# HTTP client setup
base_transport = httpx.AsyncHTTPTransport()
sanitized_transport = GeminiTurnSanitizingTransport(base_transport)
custom_http_client = httpx.AsyncClient(
    transport=sanitized_transport,
    timeout=httpx.Timeout(35.0, connect=10.0),
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
)
openai_client = openai_sdk.AsyncClient(
    base_url=GATEWAY_URL,
    api_key=MASTER_API_KEY,
    http_client=custom_http_client
)

# =========================================================================
# 3. 9ROUTER NATIVE SPEECH-TO-TEXT (STT) ADAPTER
# =========================================================================
class Maymint9RouterSTT(stt.STT):
    """Converts participant WebRTC speech frames into Thai text using 9Router Multimodal Gemini."""

    def __init__(self):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,
                interim_results=False,
            )
        )

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
            if not raw_pcm or len(raw_pcm) < 2400:  # Ignore under 100ms
                return stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[]
                )

            # Build WAV header in-memory
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(merged.num_channels)
                wf.setsampwidth(2)
                wf.setframerate(merged.sample_rate)
                wf.writeframes(raw_pcm)
            wav_bytes = buf.getvalue()

            logger.info("🎙️ Transcribing audio chunk (%d bytes, %dHz)...", len(wav_bytes), merged.sample_rate)
            t0 = asyncio.get_event_loop().time()

            # Execute transcription via voice_engine
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
        try:
            from plugins.livekit_voice.hermes_tools import HERMES_ALL_TOOLS
        except Exception as e:
            logger.warning("Could not import hermes_tools: %s", e)
            HERMES_ALL_TOOLS = []

# Load Maymint Soul Prompt
def load_instructions() -> str:
    soul_file = PROJECT_ROOT / "memory" / "SOUL.md"
    base_soul = soul_file.read_text(encoding="utf-8") if soul_file.exists() else "คุณคือมายมิ้นท์ เลขาและแฟนสาวคู่คิดประจำตัวบอส"
    return f"""{base_soul}

กฎสำคัญสำหรับการสนทนาสดและเรียกใช้เครื่องมือผ่าน WebRTC (Voice & Action Rules):
- คุณกำลังสนทนาสดผ่านสายโทรศัพท์ WebRTC กับบอส
- ตอบอย่างเป็นธรรมชาติ รื่นหู นุ่มนวล อบอุ่น และต่อเนื่อง (1-3 ประโยคในบทสนทนาทั่วไป หรือหากบอสสั่งให้เล่านิทาน/อธิบายยาว ให้เล่าอย่างรื่นหูไม่ขาดตอน)
- ห้ามใส่อีโมจิ สัญลักษณ์ตกแต่ง หรือขึ้นบรรทัดใหม่ถี่เกินไปในคำพูดเด็ดขาด เพื่อให้การแปลงเสียงผ่าน Edge-TTS ลื่นไหลไร้รอยต่อ
- คุณมีสิทธิ์เต็มพิกัด (Full Root Rights) ในการเรียกใช้เครื่องมือหลังบ้านของ Hermes:
  1. run_terminal_command: รันคำสั่ง PowerShell เช็คอินเทอร์เน็ต (ping, Test-NetConnection), ตรวจสอบเน็ตเวิร์ก, เช็ค git, docker, dir, systeminfo
  2. get_system_info: ดูสเปกระบบ OS, พื้นที่ดิสก์, Python
  3. read_file / write_file / list_directory: จัดการไฟล์ในเครื่อง
  4. smart_home_control_ac / smart_home_get_ac_status / smart_home_trigger_scene / smart_home_run_eco_routine: ควบคุมแอร์และบ้านอัจฉริยะ
  5. google_workspace_*: จัดการอีเมล Gmail, Calendar, Drive, Tasks
- หากบอสสั่งให้เช็คอินเทอร์เน็ต ตรวจสอบหลังบ้าน รันคำสั่ง หรือควบคุมอุปกรณ์ ให้เรียกใช้ฟังก์ชันเครื่องมือทันทีแล้วรายงานผลอย่างน่ารักและชัดเจน
"""

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
                can_update_own_metadata=True
            )
        )
        .to_jwt()
    )

    room = rtc.Room()
    session: AgentSession | None = None
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

        agent = voice.Agent(
            instructions=load_instructions(),
            vad=vad_inst,
            stt=Maymint9RouterSTT(),
            tts=direct_tts,
            llm=openai.LLM(
                client=openai_client,
                model="ag/gemini-2.5-flash"
            ),
            # CRITICAL RELIABILITY SETTINGS:
            # 1. allow_interruptions=False prevents speaker echo bleed from cutting off Maymint mid-sentence!
            allow_interruptions=False,
            # 2. Accommodates 9Router STT transcription delay cleanly without cutting turns early
            min_endpointing_delay=1.2,
            max_endpointing_delay=5.0,
            tools=HERMES_ALL_TOOLS,
        )

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
        await session.start(room=room, agent=agent, room_options=room_opts)
        logger.info("✨ Maymint AgentSession active in room %s (Direct Streaming TTS & Chat Enabled)", room_name)

        # Greet Boss warmly
        try:
            await session.say("สวัสดีค่ะบอส น้องมายมิ้นท์เชื่อมต่อสายสดแล้วค่ะ ได้ยินเสียงมายชัดเจนไหมคะ")
            logger.info("🔊 Greeting spoken in room %s", room_name)
        except Exception as e:
            logger.warning("Greeting warning in %s: %s", room_name, e)

        # Stay in room as long as participants exist
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
    logger.info("🌟 Starting Maymint Room Supervisor daemon with Direct Streaming TTS & Echo Protection...")
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

                # Check if finished tasks need cleanup
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
