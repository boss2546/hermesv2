"""End-to-end integration test for Smart Home voice & chat via /api/chat endpoint."""

import sys
import json
import time
import requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://127.0.0.1:9229"

def run_test():
    print("=" * 65)
    print(" 🏠 REALTIME VOICE DASHBOARD — SMART HOME END-TO-END TEST")
    print("=" * 65)

    # 1. Clear conversation history to start clean
    print("\n🧹 Clearing conversation context...")
    try:
        res = requests.post(f"{BASE_URL}/api/clear-history", timeout=5)
        print("Context cleared:", res.json())
    except Exception as e:
        print("Clear history failed:", e)

    # TEST 1: Check AC Status
    print("\n👉 [TEST 1] Testing AC Status query via voice/chat...")
    print("User: 'มาย ตอนนี้แอร์ในบ้านเปิดอยู่ไหม แล้วตั้งไว้กี่องศาคะ'")
    t0 = time.time()
    try:
        res1 = requests.post(f"{BASE_URL}/api/chat", json={
            "text": "มาย ตอนนี้แอร์ในบ้านเปิดอยู่ไหม แล้วตั้งไว้กี่องศาคะ"
        }, timeout=60).json()
        duration1 = round(time.time() - t0, 2)
        tool_events1 = res1.get("tool_events", [])
        print(f"✅ Response received in {duration1}s | Tool calls: {len(tool_events1)}")
        for ev in tool_events1:
            print(f"   [Tool] {ev.get('tool')}")
            print(f"   [Args] {ev.get('args')}")
            print(f"   [Result] {ev.get('result')}")
        print(f"   [Assistant Reply] {res1.get('reply_text')}")
        print(f"   [Audio URL] {res1.get('audio_url')}")
    except Exception as e:
        print("❌ Test 1 Error:", e)

    # TEST 2: Control AC (Set to 25 degrees)
    print("\n👉 [TEST 2] Testing AC Control via voice/chat...")
    print("User: 'มาย ช่วยปรับแอร์เป็น 25 องศาให้บอสหน่อยนะคะ'")
    t0 = time.time()
    try:
        res2 = requests.post(f"{BASE_URL}/api/chat", json={
            "text": "มาย ช่วยปรับแอร์เป็น 25 องศาให้บอสหน่อยนะคะ"
        }, timeout=60).json()
        duration2 = round(time.time() - t0, 2)
        tool_events2 = res2.get("tool_events", [])
        print(f"✅ Response received in {duration2}s | Tool calls: {len(tool_events2)}")
        for ev in tool_events2:
            print(f"   [Tool] {ev.get('tool')}")
            print(f"   [Args] {ev.get('args')}")
            print(f"   [Result] {ev.get('result')}")
        print(f"   [Assistant Reply] {res2.get('reply_text')}")
        print(f"   [Audio URL] {res2.get('audio_url')}")
    except Exception as e:
        print("❌ Test 2 Error:", e)

    print("\n" + "=" * 65)
    print("🎉 END-TO-END TEST COMPLETED!")
    print("=" * 65)

if __name__ == "__main__":
    run_test()
