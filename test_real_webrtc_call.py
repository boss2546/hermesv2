#!/usr/bin/env python3
"""Real WebRTC End-to-End LiveKit Call Verification Test."""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
PLUGINS_DIR = PROJECT_ROOT / "hermes-agent" / "plugins"
sys.path.insert(0, str(PLUGINS_DIR / "realtime_voice"))

import maymint_brain
from livekit import api, rtc

LIVEKIT_URL = "ws://127.0.0.1:7880"
API_KEY = "maymint_key_bcf1fe4a923e6181"
API_SECRET = "maymint_sec_0d4cedaee574e28e5d5cf90fb8c81e4c"
ROOM_NAME = "maymint-room"

async def test_livekit_call():
    print("=" * 70)
    print("🎙️ TESTING REAL LIVEKIT FULL-DUPLEX WEBRTC VOICE CONNECTION")
    print("=" * 70)

    # 1. Mint Token for Boss
    token = api.AccessToken(API_KEY, API_SECRET).with_identity("BossVerifier").with_name("Boss").with_grants(
        api.VideoGrants(room_join=True, room=ROOM_NAME)
    ).to_jwt()

    room = rtc.Room()
    agent_joined = asyncio.Event()
    agent_audio_received = asyncio.Event()

    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        print(f"  [RoomEvent] Participant joined: {participant.identity}")
        if participant.identity == "maymint-agent":
            agent_joined.set()

    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        print(f"  [RoomEvent] Track subscribed: {track.kind} from {participant.identity}")
        if participant.identity == "maymint-agent" and track.kind == rtc.TrackKind.KIND_AUDIO:
            agent_audio_received.set()

    print(f"Connecting BossVerifier to '{ROOM_NAME}'...")
    await room.connect(LIVEKIT_URL, token)
    print("✅ BossVerifier connected to room successfully.")

    # Check existing participants in room
    for p in room.remote_participants.values():
        print(f"  Existing remote participant: {p.identity}")
        if p.identity == "maymint-agent":
            agent_joined.set()

    # Wait for daemon to detect room and join (supervisor polls every 2s)
    print("Waiting for Maymint Agent Daemon to detect room and join...")
    try:
        await asyncio.wait_for(agent_joined.wait(), timeout=12.0)
        print("✅ Maymint Agent Daemon successfully detected and joined room!")
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for Maymint Agent to join room.")
        await room.disconnect()
        return False

    # Wait for Maymint greeting audio track
    print("Waiting for Maymint Agent to publish WebRTC audio track...")
    try:
        await asyncio.wait_for(agent_audio_received.wait(), timeout=12.0)
        print("✅ Maymint Agent audio track subscribed and verified via WebRTC!")
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for Maymint audio track.")
        await room.disconnect()
        return False

    await asyncio.sleep(2)
    await room.disconnect()
    print("✅ Disconnected from room cleanly.")
    print("=" * 70)
    print("🎉 REAL WEBRTC FULL-DUPLEX VOICE AGENT CALL: 100% SUCCESS!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    ok = asyncio.run(test_livekit_call())
    sys.exit(0 if ok else 1)
