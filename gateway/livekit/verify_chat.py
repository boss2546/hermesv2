import asyncio
import json
import livekit.api as api
from livekit import rtc

LIVEKIT_URL = "ws://127.0.0.1:7880"
API_KEY = "devkey"
API_SECRET = "secret"
ROOM_NAME = "chat-verify-room"

async def test_chat():
    token = api.AccessToken(API_KEY, API_SECRET) \
        .with_identity("chat-test-user") \
        .with_name("Chat Tester") \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=ROOM_NAME,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        )).to_jwt()

    room = rtc.Room()

    agent_replied = asyncio.Event()

    @room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket):
        topic = getattr(data_packet, 'topic', None)
        text = data_packet.data.decode("utf-8", errors="ignore")
        print(f"[RECV DATA] Topic: {topic}, Text: {text}")

    @room.on("participant_connected")
    def on_p_connected(p):
        print(f"[PARTICIPANT CONNECTED] {p.identity}")

    print(f"Connecting user to {ROOM_NAME}...")
    await room.connect(LIVEKIT_URL, token)
    print("User connected! Waiting 4s for Maymint to join and finish greeting...")
    await asyncio.sleep(4)

    # Send chat message via stream_bytes / publish_data with topic 'lk.chat' or 'lk-chat-topic'
    # In livekit-agents, room_io listens for text streams on 'lk.chat'
    print("Sending text chat message 'สวัสดีน้องมายมิ้นท์ สบายดีไหม' via stream_text / data...")
    writer = await room.local_participant.stream_text(
        topic="lk.chat",
        total_size=None
    )
    await writer.write("สวัสดีน้องมายมิ้นท์ สบายดีไหม")
    await writer.aclose()
    print("Chat message sent! Waiting 8s for response...")

    await asyncio.sleep(8)
    await room.disconnect()
    print("Test completed.")

if __name__ == "__main__":
    asyncio.run(test_chat())
