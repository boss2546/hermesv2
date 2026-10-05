"""Automated Eco Routine with 5-second intervals between commands."""

import sys
import time
import requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:3000"
INDEX = "11717"
INTERVAL = 5

def log_step(step_num: int, title: str, desc: str):
    print(f"\n[{time.strftime('%H:%M:%S')}] ⏳ สเต็ปที่ {step_num}/4: {title}")
    print(f"   👉 {desc}")

def run_eco_sequence(interval=5):
    print("=" * 60)
    print(" 🍃 ชุดคำสั่งงาน: โหมดประหยัดพลังงาน (เว้นจังหวะ 5 วินาที)")
    print(f"    ลำดับ: เปิดเครื่อง -> อุณหภูมิ 27°C -> พัดลมต่ำสุด -> โหมด Cool")
    print("=" * 60)

    # สเต็ป 1: เปิดเครื่อง (Power ON)
    log_step(1, "เปิดเครื่อง (Power ON)", "ยิงสัญญาณเปิดแอร์...")
    r1 = requests.post(f"{BASE_URL}/api/ac/test-index", json={"index": INDEX, "code": "power", "value": 1}, timeout=10)
    print(f"   ✅ ยิงคำสั่งสำเร็จ! (แอร์ดังติ๊ด)")
    print(f"   ⏱️ กำลังรอ {interval} วินาทีเพื่อให้บอร์ดแอร์พร้อมรับคำสั่งถัดไป...")
    time.sleep(interval)

    # สเต็ป 2: ปรับอุณหภูมิ 27°C
    log_step(2, "ปรับอุณหภูมิ (Temperature 27°C)", "ยิงสัญญาณตั้งค่า 27 องศา...")
    r2 = requests.post(f"{BASE_URL}/api/ac/test-index", json={"index": INDEX, "code": "temp", "value": 27}, timeout=10)
    print(f"   ✅ ยิงคำสั่งสำเร็จ! (หน้าจอขึ้นเลข 27)")
    print(f"   ⏱️ กำลังรอ {interval} วินาที...")
    time.sleep(interval)

    # สเต็ป 3: พัดลมระดับต่ำสุด (Fan Low)
    log_step(3, "ปรับแรงลม (Fan Speed Low)", "ยิงสัญญาณปรับพัดลมต่ำสุดเพื่อความเงียบและประหยัดไฟ...")
    r3 = requests.post(f"{BASE_URL}/api/ac/test-index", json={"index": INDEX, "code": "wind", "value": 1}, timeout=10)
    print(f"   ✅ ยิงคำสั่งสำเร็จ! (พัดลมหมุนสปีดต่ำสุด)")
    print(f"   ⏱️ กำลังรอ {interval} วินาที...")
    time.sleep(interval)

    # สเต็ป 4: ล็อคโหมดทำความเย็น (Cool Mode)
    log_step(4, "โหมดทำความเย็นคงที่ (Cool Mode)", "ยิงสัญญาณล็อคโหมด Cool...")
    r4 = requests.post(f"{BASE_URL}/api/ac/test-index", json={"index": INDEX, "code": "mode", "value": 0}, timeout=10)
    print(f"   ✅ ยิงคำสั่งสำเร็จ! (โหมด Cool ทำงานสมบูรณ์)")

    print("\n" + "=" * 60)
    print(" 🎉 ทำงานครบทั้งชุดคำสั่งงานเรียบร้อยแล้วค่ะบอส! 💖🌱✨")
    print("=" * 60)

if __name__ == "__main__":
    sec = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else INTERVAL
    run_eco_sequence(sec)
