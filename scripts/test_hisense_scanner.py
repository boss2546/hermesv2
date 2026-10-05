"""Scanner and Tester for Hisense AC Remote Indices in Tuya."""

import sys
import time
import requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:3000"

# All 26 Hisense remote indices from Tuya Cloud
HISENSE_INDICES = [
    '11717', '11677', '11672', '11797', '12250',
    '4841', '7596', '7724', '7725', '5217',
    '5932', '5897', '4838', '5922', '5252',
    '6302', '2807', '4888', '337', '4332',
    '9297', '7084', '4512', '5192', '5127', '5927'
]

def test_single_index(index: str):
    print(f"\n📡 กำลังยิงสัญญาณทดสอบ Index: {index} ...")
    try:
        res = requests.post(f"{BASE_URL}/api/ac/test-index", json={"index": index, "code": "power", "value": 1}, timeout=10)
        data = res.json()
        if data.get("success") and data.get("result"):
            print(f"✅ ยิงสัญญาณสำเร็จสำหรับ Index {index} (สังเกตดูว่าแอร์ดังติ๊ดไหมคะ)")
            return True
        else:
            print(f"⚠️ ยิงสัญญาณไม่สำเร็จ: {data}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def set_active_index(index: str):
    print(f"\n⚙️ กำลังตั้งค่าให้ Index {index} เป็นรีโมทแอร์ตัวหลักในระบบ...")
    try:
        res = requests.post(f"{BASE_URL}/api/ac/set-index", json={"index": index, "name": "Air"}, timeout=10)
        data = res.json()
        if data.get("success"):
            print(f"🎉 ตั้งค่าสำเร็จแล้วค่ะ! ตอนนี้ระบบใช้รหัส Index {index} เรียบร้อยแล้ว")
            return True
        else:
            print(f"⚠️ ตั้งค่าไม่สำเร็จ: {data}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def scan_top_candidates(pause_seconds=4):
    top = ['11717', '11677', '11672', '11797', '12250', '4841', '7596']
    print(f"🔍 เริ่มยิงทดสอบกลุ่มตัวเต็ง DG11 จำนวน {len(top)} รหัส (เว้นจังหวะ {pause_seconds} วินาที):")
    for idx in top:
        test_single_index(idx)
        print(f"⏳ รอ {pause_seconds} วินาที...")
        time.sleep(pause_seconds)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "scan":
            scan_top_candidates()
        elif cmd == "set" and len(sys.argv) > 2:
            set_active_index(sys.argv[2])
        else:
            test_single_index(sys.argv[1])
    else:
        print("Usage:")
        print("  python scripts/test_hisense_scanner.py <index>      (ทดสอบยิง 1 รหัส)")
        print("  python scripts/test_hisense_scanner.py scan         (ทดสอบยิงกลุ่มตัวเต็ง)")
        print("  python scripts/test_hisense_scanner.py set <index>  (ตั้งค่ารหัสนี้เป็นรีโมทจริง)")
