"""Tool definitions and handlers for the Smart Home plugin."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from .client import SmartHomeClient

logger = logging.getLogger(__name__)

# Single client instance
_client = SmartHomeClient()

# ------------------------------------------------------------------------------
# 1. smart_home_control_ac Tool Schema
# ------------------------------------------------------------------------------
SMART_HOME_CONTROL_AC_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "smart_home_control_ac",
        "description": "ควบคุมเครื่องปรับอากาศ (แอร์) ในบ้าน สั่งเปิด/ปิด ปรับอุณหภูมิ เปลี่ยนโหมดการทำงาน (cool, auto, dry, fan) และปรับระดับแรงลม",
        "parameters": {
            "type": "object",
            "properties": {
                "power": {
                    "type": "boolean",
                    "description": "เปิดแอร์ (true) หรือ ปิดแอร์ (false)"
                },
                "temperature": {
                    "type": "integer",
                    "description": "อุณหภูมิที่ต้องการปรับ เช่น 24, 25, 26 (ระหว่าง 16 ถึง 30 องศาเซลเซียส)"
                },
                "mode": {
                    "type": "string",
                    "enum": ["cool", "auto", "fan", "dry", "heat"],
                    "description": "โหมดการทำงานของแอร์: cool (ทำความเย็น), auto (อัตโนมัติ), fan (พัดลม), dry (ลดความชื้น)"
                },
                "wind_speed": {
                    "type": "string",
                    "enum": ["auto", "low", "medium", "high"],
                    "description": "ระดับแรงลมของแอร์: auto, low (เบา), medium (ปานกลาง), high (แรงสุด)"
                },
                "swing": {
                    "type": "string",
                    "enum": ["on", "off"],
                    "description": "เปิดหรือปิดการส่ายของบานสวิงแอร์"
                },
                "eco": {
                    "type": "boolean",
                    "description": "เปิดหรือปิดโหมดประหยัดพลังงาน (Eco mode)"
                }
            }
        }
    }
}

# ------------------------------------------------------------------------------
# 2. smart_home_get_ac_status Tool Schema
# ------------------------------------------------------------------------------
SMART_HOME_GET_AC_STATUS_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "smart_home_get_ac_status",
        "description": "ตรวจสอบสถานะปัจจุบันของแอร์ (เปิดหรือปิดอยู่ อุณหภูมิกี่องศา โหมดอะไร แรงลมระดับไหน)",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}

# ------------------------------------------------------------------------------
# 3. smart_home_trigger_scene Tool Schema
# ------------------------------------------------------------------------------
SMART_HOME_TRIGGER_SCENE_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "smart_home_trigger_scene",
        "description": "สั่งทำงานฉากอัตโนมัติ (Automation Scenes) เช่น โหมดดูหนัง (Movie Night), โหมดนอนหลับ (Sleep Mode), หรือออกจากบ้าน (Leave Home / ปิดทุกอย่าง)",
        "parameters": {
            "type": "object",
            "properties": {
                "scene_id": {
                    "type": "string",
                    "enum": ["scene-movie-night", "scene-eco-sleep", "scene-leave-home", "scene-cinema-xiaomi"],
                    "description": "รหัสฉากที่ต้องการสั่ง: 'scene-movie-night' (ดูหนัง), 'scene-eco-sleep' (เข้านอน), 'scene-leave-home' (ปิดหมดก่อนออกจากบ้าน), 'scene-cinema-xiaomi' (เปิดโฮมเธียเตอร์)"
                }
            },
            "required": ["scene_id"]
        }
    }
}

SMART_HOME_TOOLS = [
    SMART_HOME_CONTROL_AC_SCHEMA,
    SMART_HOME_GET_AC_STATUS_SCHEMA,
    SMART_HOME_TRIGGER_SCENE_SCHEMA
]


def execute_smart_home_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a smart home tool and return dictionary result."""
    client = SmartHomeClient()
    try:
        if name == "smart_home_control_ac":
            power = args.get("power")
            temp = args.get("temperature")
            mode = args.get("mode")
            wind = args.get("wind_speed")
            swing = args.get("swing")
            eco = args.get("eco")
            return client.control_ac(
                power=power,
                temperature=temp,
                mode=mode,
                wind_speed=wind,
                swing=swing,
                eco=eco
            )

        elif name == "smart_home_get_ac_status":
            devices_res = client.get_devices()
            if not devices_res.get("success"):
                return devices_res
            remotes = devices_res.get("remotes", [])
            for r in remotes:
                if r.get("type") == "ac" or r.get("id") == client.default_ac_id:
                    return {
                        "success": True,
                        "device_name": r.get("name"),
                        "power": r.get("power"),
                        "temperature": r.get("temperature"),
                        "mode": r.get("mode"),
                        "windSpeed": r.get("windSpeed"),
                        "swing": r.get("swing"),
                        "eco": r.get("eco"),
                        "lastUpdated": r.get("lastUpdated")
                    }
            return {"success": False, "error": "ไม่พบอุปกรณ์แอร์ในระบบ"}

        elif name == "smart_home_trigger_scene":
            scene_id = args.get("scene_id")
            if not scene_id:
                return {"success": False, "error": "จำเป็นต้องระบุ scene_id"}
            return client.trigger_scene(scene_id)

        else:
            return {"success": False, "error": f"Unknown smart home tool: {name}"}

    except Exception as e:
        logger.error("Error executing %s: %s", name, e)
        return {"success": False, "error": str(e)}
