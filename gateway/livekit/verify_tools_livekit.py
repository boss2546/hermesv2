import asyncio
import livekit.api as api
from livekit import rtc

LIVEKIT_URL = "ws://127.0.0.1:7880"
API_KEY = "devkey"
API_SECRET = "secret"
ROOM_NAME = "tools-verify-room"

async def test_tools_invocation():
    token = api.AccessToken(API_KEY, API_SECRET) \
        .with_identity("tools-tester") \
        .with_name("Tools Tester") \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=ROOM_NAME,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        )).to_jwt()

    room = rtc.Room()

    @room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket):
        topic = getattr(data_packet, 'topic', None)
        text = data_packet.data.decode("utf-8", errors="ignore")
        print(f"[RECV] Topic: {topic}, Text: {text}")

    print(f"Connecting to {ROOM_NAME}...")
    await room.connect(LIVEKIT_URL, token)
    print("Connected! Waiting 4s for Maymint to join and finish greeting...")
    await asyncio.sleep(4)

    # Ask Maymint to check internet / run ping via chat
    print("Sending request: 'มายช่วยเช็คอินเทอร์เน็ตของเครื่องให้หน่อยค่ะ'...")
    writer = await room.local_participant.stream_text(
        topic="lk.chat",
        total_size=None
    )
    await writer.write("มายช่วยเช็คอินเทอร์เน็ตของเครื่องให้หน่อยค่ะ")
    await writer.aclose()
    print("Request sent! Waiting 12s for tool calling and response...")

    await asyncio.sleep(12)
    await room.disconnect()
    print("Tool verification completed.")

if __name__ == "__main__":
    asyncio.run(test_tools_invocation())
