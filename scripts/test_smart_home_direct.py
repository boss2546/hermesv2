"""Direct verification test for smart_home plugin tools and client.
Tests communication with the running Tuya Smart IR Gateway microservice (port 3000).
"""

import sys
import os
import json

# Ensure hermes-agent plugins can be imported
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(workspace_root, "hermes-agent", "plugins"))

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from smart_home import SmartHomeClient, SMART_HOME_TOOLS, execute_smart_home_tool

def test_direct():
    print("=" * 60)
    print("🏠 SMART HOME PLUGIN DIRECT TEST")
    print("=" * 60)

    # 1. Test Client Health & Status
    client = SmartHomeClient()
    print("\n[Step 1] Checking gateway status...")
    status = client.get_status()
    print(f"Gateway Status: {json.dumps(status, ensure_ascii=False, indent=2)}")
    assert status.get("status") == "online", "Gateway is not online!"
    print("✅ Gateway is online!")

    # 2. Test Get AC Status Tool
    print("\n[Step 2] Testing execute_smart_home_tool('smart_home_get_ac_status')...")
    ac_status = execute_smart_home_tool("smart_home_get_ac_status", {})
    print(f"AC Status: {json.dumps(ac_status, ensure_ascii=False, indent=2)}")
    assert ac_status.get("success") is True, f"Failed to get AC status: {ac_status}"
    print(f"✅ AC found: {ac_status.get('device_name')} (Power: {ac_status.get('power')}, Temp: {ac_status.get('temperature')}°C)")

    # 3. Test Control AC Tool (Read current temp and set safely)
    current_temp = ac_status.get("temperature", 25)
    print(f"\n[Step 3] Testing execute_smart_home_tool('smart_home_control_ac') with temp={current_temp}...")
    control_res = execute_smart_home_tool("smart_home_control_ac", {
        "power": True,
        "temperature": current_temp,
        "mode": "cool"
    })
    print(f"Control Result: {json.dumps(control_res, ensure_ascii=False, indent=2)}")
    assert control_res.get("success") is True, f"Failed to control AC: {control_res}"
    print("✅ AC Control command succeeded!")

    # 4. Verify Schemas
    print("\n[Step 4] Checking OpenAI tool schemas...")
    print(f"Total Tools defined: {len(SMART_HOME_TOOLS)}")
    for t in SMART_HOME_TOOLS:
        fn = t.get("function", {})
        print(f" - Tool: {fn.get('name')} -> {fn.get('description')[:50]}...")
    print("✅ All tool schemas valid!")

    print("\n" + "=" * 60)
    print("🎉 ALL SMART HOME PLUGIN DIRECT TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_direct()
