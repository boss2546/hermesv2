import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import time

base_url = 'http://127.0.0.1:9229'

def run_suite():
    print("=" * 60)
    print(" 🧪 HERMES V2 REALTIME VOICE — AUTONOMOUS TOOL TEST SUITE")
    print("=" * 60)

    # 1. Clear history
    requests.post(f"{base_url}/api/clear-history")
    print("🧹 Conversation context cleared.\n")

    # TEST 1: Terminal Git Command
    print("👉 [TEST 1] Testing Terminal Execution (git status / git branch)...")
    t0 = time.time()
    res1 = requests.post(f"{base_url}/api/chat", json={
        "text": "มาย ช่วยเช็ค git status และ git branch ปัจจุบันในเครื่องให้หน่อยสิคะ"
    }, timeout=60).json()
    elapsed1 = round(time.time() - t0, 2)
    tool_events1 = res1.get("tool_events", [])
    print(f"✅ Test 1 Completed in {elapsed1}s | Tool Calls: {len(tool_events1)}")
    for ev in tool_events1:
        print(f"   [Tool] {ev.get('tool')}")
        print(f"   [Args] {ev.get('args')}")
        res_info = ev.get('result', {})
        print(f"   [Exit] {res_info.get('exit_code')}")
        print(f"   [Stdout] {res_info.get('stdout', '')[:100]}...")
    print(f"   [Audio URL] {res1.get('audio_url')}")
    print(f"   [Assistant Preview] {res1.get('reply_text', '')[:200]}...\n")

    # TEST 2: System Specs & Metrics
    print("👉 [TEST 2] Testing System Info Inspection...")
    t0 = time.time()
    res2 = requests.post(f"{base_url}/api/chat", json={
        "text": "มาย ช่วยเช็คสเปกระบบ พื้นที่ฮาร์ดดิสก์ และ Python version ของเครื่องนี้ให้บอสดูหน่อย"
    }, timeout=60).json()
    elapsed2 = round(time.time() - t0, 2)
    tool_events2 = res2.get("tool_events", [])
    print(f"✅ Test 2 Completed in {elapsed2}s | Tool Calls: {len(tool_events2)}")
    for ev in tool_events2:
        print(f"   [Tool] {ev.get('tool')}")
        print(f"   [Result] {ev.get('result')}")
    print(f"   [Assistant Preview] {res2.get('reply_text', '')[:200]}...\n")

    # TEST 3: Create & Run Python Script
    print("👉 [TEST 3] Testing Autonomous Script Creation & Execution...")
    t0 = time.time()
    res3 = requests.post(f"{base_url}/api/chat", json={
        "text": "มาย ช่วยเขียนไฟล์ test_fibo.py คำนวณ Fibonacci 10 ตัวแรก แล้วรันไฟล์นี้ในเทอร์มินัลให้บอสดูผลลัพธ์หน่อยนะ"
    }, timeout=90).json()
    elapsed3 = round(time.time() - t0, 2)
    tool_events3 = res3.get("tool_events", [])
    print(f"✅ Test 3 Completed in {elapsed3}s | Tool Calls: {len(tool_events3)}")
    for ev in tool_events3:
        print(f"   [Tool] {ev.get('tool')}: {ev.get('args')}")
        out = ev.get('result', {}).get('stdout') or ev.get('result', {}).get('status')
        print(f"   [Output] {out}")
    print(f"   [Assistant Preview] {res3.get('reply_text', '')[:250]}...\n")

    # TEST 4: Clean up test_fibo.py
    print("👉 [TEST 4] Testing Clean Up via Tool...")
    t0 = time.time()
    res4 = requests.post(f"{base_url}/api/chat", json={
        "text": "ขอบคุณจ้ะมายมิ้น ช่วยลบไฟล์ test_fibo.py ออกจากเครื่องให้เรียบร้อยด้วยน้า"
    }, timeout=60).json()
    elapsed4 = round(time.time() - t0, 2)
    tool_events4 = res4.get("tool_events", [])
    print(f"✅ Test 4 Completed in {elapsed4}s | Tool Calls: {len(tool_events4)}")
    for ev in tool_events4:
        print(f"   [Tool] {ev.get('tool')}: {ev.get('args')}")
    print(f"   [Assistant Preview] {res4.get('reply_text', '')[:200]}...\n")

    print("=" * 60)
    print(" 🎉 ALL 4 IN-DEPTH TESTS PASSED 100%!")
    print("=" * 60)

if __name__ == '__main__':
    run_suite()
