"""Step-by-step isolated AC command tester for Boss."""

import sys
import time
import requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:3000"
REMOTE_ID = "a35a4e0b12b02aa750ceh4"

def step_power_on(index="11717"):
    print(f"\n=======================================================")
    print(f"👉 [สเต็ปที่ 1] ยิงคำสั่ง: เปิดเครื่อง (Power ON) เดี่ยวๆ")
    print(f"   รหัส Index: {index}")
    print(f"=======================================================")
    res = requests.post(f"{BASE_URL}/api/ac/test-index", json={
        "index": index,
        "code": "power",
        "value": 1
    }, timeout=10)
    data = res.json()
    print("ผลลัพธ์จากฮับ:", data)
    if data.get("success"):
        print("✅ ยิงสัญญาณ Power ON สำเร็จเรียบร้อยแล้วค่ะ!")
        print("👀 บอสสังเกตดูนะคะ: มีเสียงติ๊ด และบานสวิงเริ่มขยับเปิดไหมคะ?")
    else:
        print("❌ เกิดข้อผิดพลาด:", data)

def step_power_off(index="11717"):
    print(f"\n=======================================================")
    print(f"👉 [สเต็ปคำสั่ง] ยิงคำสั่ง: ปิดเครื่อง (Power OFF) เดี่ยวๆ")
    print(f"   รหัส Index: {index}")
    print(f"=======================================================")
    res = requests.post(f"{BASE_URL}/api/ac/test-index", json={
        "index": index,
        "code": "power",
        "value": 0
    }, timeout=10)
    data = res.json()
    print("ผลลัพธ์จากฮับ:", data)
    if data.get("success"):
        print("✅ ยิงสัญญาณ Power OFF สำเร็จเรียบร้อยแล้วค่ะ!")
    else:
        print("❌ เกิดข้อผิดพลาด:", data)

def step_set_temp(temp=25):
    print(f"\n=======================================================")
    print(f"👉 [สเต็ปถัดไป] ยิงคำสั่งปรับอุณหภูมิเดี่ยวๆ: {temp}°C")
    print(f"=======================================================")
    res = requests.post(f"{BASE_URL}/api/remotes/{REMOTE_ID}/command", json={
        "power": True,
        "temperature": temp
    }, timeout=10)
    print("ผลลัพธ์:", res.json().get('results'))

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "on"
    idx = sys.argv[2] if len(sys.argv) > 2 else "11717"
    if action == "on":
        step_power_on(idx)
    elif action == "off":
        step_power_off(idx)
    elif action == "temp":
        t = int(idx) if idx.isdigit() else 25
        step_set_temp(t)
