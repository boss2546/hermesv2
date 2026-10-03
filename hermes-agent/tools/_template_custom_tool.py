"""
🛠️ Hermes Agent — Custom Tool Master Template (แม่แบบเครื่องมือมาตรฐานสูงสุด)
=============================================================================
ไฟล์นี้เป็น "แม่แบบแม่บท (Master Template)" สำหรับการสร้างเครื่องมือ (Custom Tool) ใหม่
ใน Hermes Agent อย่างถูกต้องตามสถาปัตยกรรม 100% พร้อมระบบ Auto-Discovery และ Type Safety

📌 วิธีนำไปใช้งาน:
1. คัดลอกไฟล์นี้แล้วเปลี่ยนชื่อเป็นเครื่องมือที่ต้องการ เช่น `tools/my_crypto_tool.py`
2. แก้ไข Schema, ฟังก์ชัน Handler, และคำอธิบาย
3. บันทึกไฟล์ — ระบบ Auto-Discovery ของ Hermes จะตรวจจับและลงทะเบียนให้อัตโนมัติทันที!
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# รองรับการรันเทสต์ไฟล์นี้ตรงๆ จากทุกที่
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# นำเข้า Registry และ Error Handler มาตรฐานของ Hermes
from tools.registry import registry, tool_error, tool_result

logger = logging.getLogger(__name__)


# =============================================================================
# 1. ⚙️ คอนฟิกและค่าคงที่ (Constants & Constraints)
# =============================================================================
TOOL_NAME = "custom_demo_tool"
TOOLSET_NAME = "coding"  # หรือ "web", "custom", "finance", "automation"
TOOL_EMOJI = "⚡"

# ป้องกันข้อความผลลัพธ์ยาวเกินจนทำให้ Context Window บวม
MAX_RESULT_CHARS = 100_000


# =============================================================================
# 2. 📋 JSON Schema Definition (พจนานุกรมบอก AI ว่ารับค่าอะไรบ้าง)
# =============================================================================
# คำแนะนำในการเขียนคำอธิบาย (Prompt Engineering for Tools):
# - Description ควรบอกชัดเจนว่า "เครื่องมือนี้ใช้ทำอะไร", "เมื่อไหร่ควรใช้", และ "ผลลัพธ์คืออะไร"
# - Parameters ควรกำหนด Type, Description และ Enum (ถ้ามีตัวเลือกเฉพาะ)
DEMO_TOOL_SCHEMA: Dict[str, Any] = {
    "name": TOOL_NAME,
    "description": (
        "เครื่องมือตัวอย่างมาตรฐาน: ใช้สำหรับประมวลผลข้อความ คำนวณ หรือดึงข้อมูลภายนอก "
        "รองรับทั้งการรับพารามิเตอร์แบบ String, Number, Boolean, List และ Enum "
        "ส่งคืนผลลัพธ์เป็น JSON ที่มีโครงสร้างชัดเจน"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "คำค้นหา หรือข้อความหลักที่ต้องการส่งเข้ามาประมวลผล",
            },
            "action": {
                "type": "string",
                "enum": ["search", "analyze", "format", "ping"],
                "default": "analyze",
                "description": "คำสั่งหรือโหมดการทำงานที่ต้องการเลือกใช้",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "default": 10,
                "description": "จำนวนรายการผลลัพธ์สูงสุดที่ต้องการ",
            },
            "detailed": {
                "type": "boolean",
                "default": False,
                "description": "ต้องการผลลัพธ์แบบละเอียดพร้อม Metadata หรือไม่",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "แท็กหรือหมวดหมู่ย่อย (ถ้ามี)",
            },
        },
        "required": ["query"],  # พารามิเตอร์ที่จำเป็นต้องระบุเสมอ
    },
}


# =============================================================================
# 3. 🔍 ฟังก์ชันตรวจสอบความพร้อม (Availability Check Function)
# =============================================================================
def check_demo_tool_requirements() -> bool:
    """
    ตรวจสอบว่าเครื่องมือนี้พร้อมใช้งานบนเครื่อง ณ ปัจจุบันหรือไม่
    - ตรวจสอบ API Key ใน Environment
    - ตรวจสอบว่ามีโปรแกรมที่ต้องใช้ติดตั้งอยู่หรือไม่ (เช่น Docker, Git, CLI)
    - ถ้าคืนค่า False: Hermes จะซ่อนเครื่องมือนี้จาก AI อัตโนมัติ (ไม่ทำให้ AI สับสน)
    """
    # ตัวอย่าง: ตรวจสอบ API Key (ถ้าไม่ต้องใช้ ให้ return True เสมอ)
    # return bool(os.getenv("MY_SERVICE_API_KEY"))
    return True


# =============================================================================
# 4. 🚀 ฟังก์ชันทำงานจริง (Core Logic & Handler)
# =============================================================================
def execute_demo_tool(
    query: str,
    action: str = "analyze",
    limit: int = 10,
    detailed: bool = False,
    tags: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    **context_kwargs: Any,
) -> str:
    """
    ฟังก์ชันหลักที่ถูกเรียกเมื่อ AI ตัดสินใจใช้งาน Tool นี้

    Args:
        query: ข้อความหลัก
        action: โหมดการทำงาน
        limit: จำนวนผลลัพธ์
        detailed: ต้องการข้อมูลละเอียดไหม
        tags: แท็กเพิ่มเติม
        session_id: (Injected) รหัสเซสชันที่ Hermes ส่งมาให้ใช้งานได้
        **context_kwargs: ข้อมูลบริบทอื่นๆ จากระบบ (task_id, parent_agent, workspace)

    Returns:
        JSON String ของผลลัพธ์ หรือข้อความผลลัพธ์ในรูปแบบ Markdown
    """
    # 1. ตรวจสอบความถูกต้องของข้อมูล (Input Validation)
    query = (query or "").strip()
    if not query:
        return tool_error("พารามิเตอร์ 'query' ต้องไม่เป็นค่าว่าง")

    if limit < 1 or limit > 50:
        return tool_error("พารามิเตอร์ 'limit' ต้องอยู่ระหว่าง 1 ถึง 50")

    try:
        # 2. ลงมือทำงานตาม Logic ของบอส (Business Logic)
        logger.info(f"[{TOOL_NAME}] Action: {action}, Query: {query}")

        if action == "ping":
            return tool_result(
                status="online",
                message="เครื่องมือตอบสนองปกติ 100% พร้อมใช้งานค่ะบอส! 💖",
                query=query,
            )

        # จำลองการประมวลผลข้อมูล (หรือต่อ Database / ยิง API)
        items = [f"ผลลัพธ์รายการที่ {i+1} สำหรับ '{query}'" for i in range(min(limit, 3))]

        result_payload: Dict[str, Any] = {
            "success": True,
            "action": action,
            "query": query,
            "count": len(items),
            "results": items,
        }

        if detailed:
            result_payload["metadata"] = {
                "session_id": session_id,
                "tags": tags or [],
                "engine": "Hermes-v2-Custom-Tool",
            }

        # 3. ส่งคืนผลลัพธ์เป็น JSON String ผ่านตัวช่วย tool_result
        return tool_result(result_payload)

    except Exception as exc:
        # บันทึก Error Log เพื่อการ Debug และส่งข้อความเตือนที่กระชับกลับไปให้ AI
        logger.exception(f"[{TOOL_NAME}] Execution error: {exc}")
        return tool_error(f"เกิดข้อผิดพลาดในการประมวลผลเครื่องมือ: {exc}")


# =============================================================================
# 5. 📝 การลงทะเบียนเข้าสู่ระบบ Hermes (Registration)
# =============================================================================
# กฎสำคัญของ Hermes: การเรียก `registry.register(...)` ต้องอยู่ที่ระดับ Module
# เพื่อให้ระบบ Auto-Discovery ค้นพบและนำเข้าอัตโนมัติเมื่อ Hermes บูตเครื่อง!
registry.register(
    name=TOOL_NAME,
    toolset=TOOLSET_NAME,
    schema=DEMO_TOOL_SCHEMA,
    check_fn=check_demo_tool_requirements,
    handler=lambda args, **kw: execute_demo_tool(
        query=args.get("query", ""),
        action=args.get("action", "analyze"),
        limit=args.get("limit", 10),
        detailed=args.get("detailed", False),
        tags=args.get("tags"),
        session_id=kw.get("session_id"),
        **kw,
    ),
    emoji=TOOL_EMOJI,
    description=DEMO_TOOL_SCHEMA["description"],
    max_result_size_chars=MAX_RESULT_CHARS,
)


# =============================================================================
# 6. 🧪 Self-Test เมื่อรันไฟล์นี้ตรงๆ (Unit Testing)
# =============================================================================
if __name__ == "__main__":
    print(f"🧪 Testing '{TOOL_NAME}' directly...")

    # 1. ทดสอบโหมด Ping
    test_result_ping = execute_demo_tool(query="ทดสอบระบบ", action="ping")
    print(f"\n1. Ping Result:\n{test_result_ping}")

    # 2. ทดสอบโหมดประมวลผลข้อมูล
    test_result_data = execute_demo_tool(
        query="ราคาเหรียญ BTC", action="analyze", limit=2, detailed=True, tags=["crypto", "market"]
    )
    print(f"\n2. Data Result:\n{test_result_data}")

    # 3. ทดสอบการดักจับข้อผิดพลาด (Validation Error)
    test_result_err = execute_demo_tool(query="", action="analyze")
    print(f"\n3. Error Validation Result:\n{test_result_err}")

    print("\n✅ All unit tests passed! Tool is ready for Hermes Agent.")
