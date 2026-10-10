"""Knowledge Lexicon & Command Bank for High-Precision Speech-to-Text (STT) & Voice Assistant.

Provides:
- Categorized storage for Commands, Smart Home, Google Workspace, Tech Terms, Identity, and Phonetic Corrections.
- Precision Prompt Generator for Multimodal Audio STT (Gemini 3.8/2.5) to prime speech recognition with domain vocabulary.
- Normalization Engine to automatically correct misheard words and phonetic distortions (e.g., 'เปิดแอ' -> 'เปิดแอร์').
- Thread-safe disk persistence (knowledge_lexicon.json) with full CRUD API.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("voice-lexicon")

DEFAULT_GATEWAY_URL = "https://api.meuu.club/v1"
DEFAULT_MASTER_KEY = "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"

def _resolve_api_key() -> str:
    return (
        os.getenv("MEUU_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or DEFAULT_MASTER_KEY
    )

LEXICON_FILE_PATH = Path(__file__).resolve().parent / "knowledge_lexicon.json"
_lexicon_lock = threading.RLock()

# Pre-populated Default Knowledge Bank
DEFAULT_LEXICON: Dict[str, Any] = {
    "version": "1.0",
    "updated_at": int(time.time()),
    "description": "คลังคำสั่งและคำศัพท์สำหรับถอดความเสียง ป้องกันคำเพี้ยน และจัดระเบียบบริบทระบบ",
    "categories": {
        "commands": {
            "label": "คลังคำสั่งระบบ & งาน",
            "icon": "⚡",
            "description": "ประโยคและคำสั่งหลักที่ใช้บ่อย เพื่อให้ระบบถอดความเข้าใจเจตนาคำสั่งได้อย่างแม่นยำ",
            "items": [
                {
                    "id": "cmd_ac_on",
                    "term": "เปิดแอร์",
                    "aliases": ["เปิดแอ", "เปิดเครื่องปรับอากาศ", "เปิดแอร์หน่อย", "ช่วยเปิดแอร์"],
                    "desc": "สั่งเปิดเครื่องปรับอากาศห้องนอน",
                    "category": "commands"
                },
                {
                    "id": "cmd_ac_off",
                    "term": "ปิดแอร์",
                    "aliases": ["ปิดแอ", "ดับแอร์", "ปิดเครื่องปรับอากาศ"],
                    "desc": "สั่งปิดเครื่องปรับอากาศห้องนอน",
                    "category": "commands"
                },
                {
                    "id": "cmd_ac_temp",
                    "term": "ปรับแอร์",
                    "aliases": ["ปรับอุณหภูมิ", "ตั้งแอร์", "ลดแอร์", "เพิ่มแอร์", "แอร์กี่องศา"],
                    "desc": "ปรับอุณหภูมิหรือตรวจสอบสถานะเครื่องปรับอากาศ",
                    "category": "commands"
                },
                {
                    "id": "cmd_gmail_check",
                    "term": "เช็คอีเมล",
                    "aliases": ["เช็คเมล", "ดูเมล", "อ่านอีเมล", "เปิดดูเมล", "เช็คจีเมล", "มีเมลเข้าไหม"],
                    "desc": "ค้นหาและสรุปเนื้อหาอีเมลล่าสุดใน Gmail",
                    "category": "commands"
                },
                {
                    "id": "cmd_gmail_send",
                    "term": "ส่งอีเมล",
                    "aliases": ["ส่งเมล", "เขียนอีเมล", "ส่ง mail", "ตอบกลับอีเมล"],
                    "desc": "สร้างและส่งอีเมลหาผู้รับผ่าน Gmail API",
                    "category": "commands"
                },
                {
                    "id": "cmd_cal_event",
                    "term": "สร้างนัดหมาย",
                    "aliases": ["ลงปฏิทิน", "บันทึกปฏิทิน", "เพิ่มนัดหมาย", "ลงตารางงาน", "จดตารางนัด"],
                    "desc": "สร้างกิจกรรมหรือนัดหมายใหม่ใน Google Calendar",
                    "category": "commands"
                },
                {
                    "id": "cmd_cal_list",
                    "term": "ดูตารางงาน",
                    "aliases": ["เช็คปฏิทิน", "ดูนัดหมาย", "วันนี้มีงานอะไร", "พรุ่งนี้มีอะไร"],
                    "desc": "ตรวจสอบรายการนัดหมายใน Google Calendar",
                    "category": "commands"
                },
                {
                    "id": "cmd_drive_search",
                    "term": "ค้นหาไฟล์ใน Drive",
                    "aliases": ["หาไฟล์", "ค้นไฟล์", "ดูไฟล์ในไดรฟ์", "หาเอกสารใน drive"],
                    "desc": "ค้นหาและเปิดดูเอกสารบน Google Drive",
                    "category": "commands"
                },
                {
                    "id": "cmd_git_status",
                    "term": "เช็คสถานะ Git",
                    "aliases": ["เช็คกิต", "git status", "ดูการเปลี่ยนแปลงโค้ด"],
                    "desc": "ตรวจสอบสถานะการแก้ไขโค้ดใน Repository",
                    "category": "commands"
                },
                {
                    "id": "cmd_git_push",
                    "term": "Git Commit & Push",
                    "aliases": ["กิตพุช", "พุชโค้ด", "คอมมิทโค้ด", "ดันโค้ดขึ้น github"],
                    "desc": "บันทึกและพุชการเปลี่ยนแปลงขึ้น GitHub",
                    "category": "commands"
                },
                {
                    "id": "cmd_docker_ctl",
                    "term": "จัดการ Docker",
                    "aliases": ["รันด็อกเกอร์", "รีสตาร์ทด็อกเกอร์", "เช็คคอนเทนเนอร์"],
                    "desc": "ควบคุมและตรวจสอบสถานะ Docker Container",
                    "category": "commands"
                }
            ]
        },
        "devices": {
            "label": "อุปกรณ์ Smart Home & กายภาพ",
            "icon": "🏠",
            "description": "รายชื่ออุปกรณ์ เซนเซอร์ และหน่วยวัดในบ้าน เพื่อให้ระบบแยกแยะชื่ออุปกรณ์ได้ตรงเป๊ะ",
            "items": [
                {
                    "id": "dev_ac",
                    "term": "แอร์",
                    "aliases": ["แอ", "แอร์ห้องนอน", "เครื่องปรับอากาศ"],
                    "desc": "เครื่องปรับอากาศหลัก (Daikin/Inverter)",
                    "category": "devices"
                },
                {
                    "id": "dev_ir",
                    "term": "Tuya Smart IR Gateway",
                    "aliases": ["ทูย่า", "ทูย่าเกตเวย์", "สมาร์ทไออาร์", "เกตเวย์รีโมท"],
                    "desc": "ฮับส่งสัญญาณอินฟราเรดอัจฉริยะ (พอร์ต 3000)",
                    "category": "devices"
                },
                {
                    "id": "dev_temp",
                    "term": "องศา",
                    "aliases": ["ดีกรี", "°C", "องศาเซลเซียส"],
                    "desc": "หน่วยวัดอุณหภูมิห้องและเครื่องปรับอากาศ",
                    "category": "devices"
                },
                {
                    "id": "dev_mode_cool",
                    "term": "โหมด Cool",
                    "aliases": ["โหมดคูล", "โหมดเย็น", "โหมดทำความเย็น"],
                    "desc": "โหมดทำความเย็นปกติของเครื่องปรับอากาศ",
                    "category": "devices"
                },
                {
                    "id": "dev_mode_fan",
                    "term": "โหมด Fan",
                    "aliases": ["โหมดพัดลม", "โหมดแฟน"],
                    "desc": "โหมดหมุนเวียนอากาศเฉพาะพัดลม",
                    "category": "devices"
                },
                {
                    "id": "dev_fan_speed",
                    "term": "แรงลม",
                    "aliases": ["ความเร็วพัดลม", "พัดลมแอร์", "แฟนสปีด"],
                    "desc": "ระดับความเร็วของพัดลมแอร์ (auto, low, mid, high)",
                    "category": "devices"
                }
            ]
        },
        "workspace": {
            "label": "Google Workspace & เครื่องมือทำงาน",
            "icon": "💼",
            "description": "บริการ Cloud, แอปพลิเคชันการทำงาน และเอกสารของ Google",
            "items": [
                {
                    "id": "ws_gmail",
                    "term": "Gmail",
                    "aliases": ["จีเมล์", "จีเมล", "เจเมล", "เมลกูเกิล"],
                    "desc": "บริการจัดการอีเมลของ Google",
                    "category": "workspace"
                },
                {
                    "id": "ws_drive",
                    "term": "Google Drive",
                    "aliases": ["กูเกิลไดรฟ์", "กูเกิ้ลไดร์", "เกิ้ลไดรฟ์", "คลาวด์ไดรฟ์"],
                    "desc": "พื้นที่จัดเก็บไฟล์และเอกสารออนไลน์",
                    "category": "workspace"
                },
                {
                    "id": "ws_cal",
                    "term": "Google Calendar",
                    "aliases": ["กูเกิลคาเลนดาร์", "คาเลนดาร์", "ปฏิทินกูเกิล"],
                    "desc": "ระบบปฏิทินและนัดหมายการทำงาน",
                    "category": "workspace"
                },
                {
                    "id": "ws_docs",
                    "term": "Google Docs",
                    "aliases": ["กูเกิลด็อก", "กูเกิลดอกส์", "ด็อกส์"],
                    "desc": "ระบบเอกสารประมวลผลคำ",
                    "category": "workspace"
                },
                {
                    "id": "ws_sheets",
                    "term": "Google Sheets",
                    "aliases": ["กูเกิลชีต", "กูเกิลชีท", "สเปรดชีต", "ชีต"],
                    "desc": "ระบบสเปรดชีตตารางคำนวณ",
                    "category": "workspace"
                },
                {
                    "id": "ws_tasks",
                    "term": "Google Tasks",
                    "aliases": ["กูเกิลแทสก์", "กูเกิลทาสก์", "แทสก์", "รายการงาน"],
                    "desc": "ระบบบันทึก To-Do List และรายการสิ่งที่ต้องทำ",
                    "category": "workspace"
                }
            ]
        },
        "technical": {
            "label": "ศัพท์เทคนิค & งานพัฒนา (Dev)",
            "icon": "💻",
            "description": "คำศัพท์วิศวกรรมซอฟต์แวร์ ฐานข้อมูล และโครงสร้างระบบ เพื่อไม่ให้สะกดเพี้ยน",
            "items": [
                {
                    "id": "tech_docker",
                    "term": "Docker",
                    "aliases": ["ด็อกเกอร์", "ดอกเกอร์"],
                    "desc": "แพลตฟอร์ม Containerization สำหรับบริการและแอป",
                    "category": "technical"
                },
                {
                    "id": "tech_python",
                    "term": "Python",
                    "aliases": ["ไพธอน", "ไพทอน"],
                    "desc": "ภาษาโปรแกรมมิ่งหลักของ Agent และ Backend",
                    "category": "technical"
                },
                {
                    "id": "tech_postgres",
                    "term": "PostgreSQL",
                    "aliases": ["โพสเกรส", "โพสต์เกรส", "โพสเกรสคิวแอล"],
                    "desc": "ระบบจัดการฐานข้อมูล Relational Database",
                    "category": "technical"
                },
                {
                    "id": "tech_mysql",
                    "term": "MySQL",
                    "aliases": ["มายเอสคิวแอล", "มายซีเควล"],
                    "desc": "ระบบฐานข้อมูล MySQL 8.4+ utf8mb4",
                    "category": "technical"
                },
                {
                    "id": "tech_nginx",
                    "term": "NGINX",
                    "aliases": ["เอนจิ้นเอ็กซ์", "เอ็นจินเอ็กซ์", "เอนจินเอกซ์"],
                    "desc": "Reverse Proxy และ Web Server Gateway",
                    "category": "technical"
                },
                {
                    "id": "tech_cloudflare",
                    "term": "Cloudflare",
                    "aliases": ["คลาวด์แฟลร์", "คลาวด์แฟร์"],
                    "desc": "เครือข่าย Cloudflare Tunnel & CDN SSL",
                    "category": "technical"
                },
                {
                    "id": "tech_github",
                    "term": "GitHub",
                    "aliases": ["กิตฮับ", "กิทฮับ", "กิตฮับดอทคอม"],
                    "desc": "ระบบ Git Version Control ทางไกล",
                    "category": "technical"
                },
                {
                    "id": "tech_api",
                    "term": "API Gateway",
                    "aliases": ["เอพีไอ", "เกตเวย์", "9Router"],
                    "desc": "เกตเวย์เชื่อมต่อโมเดล AI (api.meuu.club)",
                    "category": "technical"
                },
                {
                    "id": "tech_migrate",
                    "term": "Migrate",
                    "aliases": ["ไมเกรต", "ย้ายข้อมูล", "การไมเกรต"],
                    "desc": "กระบวนการย้ายและแปลงโครงสร้างฐานข้อมูล",
                    "category": "technical"
                },
                {
                    "id": "tech_token",
                    "term": "Token",
                    "aliases": ["โทเคน", "โทเค็น"],
                    "desc": "รหัสสิทธิ์ยืนยันตัวตนความปลอดภัย OAuth2 / Bearer",
                    "category": "technical"
                }
            ]
        },
        "identity": {
            "label": "บุคคล & อัตลักษณ์",
            "icon": "💖",
            "description": "ชื่อเรียก บทบาท และตัวตนของบอสและน้องมายมิ้นท์",
            "items": [
                {
                    "id": "id_maymint",
                    "term": "มายมิ้นท์",
                    "aliases": ["มายมิน", "มายมิ่น", "น้องมาย", "มาย", "Maymint"],
                    "desc": "แฟนสาวคู่คิดและเลขาประจำตัวของบอส",
                    "category": "identity"
                },
                {
                    "id": "id_boss",
                    "term": "บอส",
                    "aliases": ["บอสส์", "คุณบอส", "พี่บอส", "Boss"],
                    "desc": "คนสำคัญอันดับ 1 ในใจของมายมิ้นท์",
                    "category": "identity"
                },
                {
                    "id": "id_hermes",
                    "term": "Hermes Agent",
                    "aliases": ["เฮอร์มีส", "เฮอมิส", "Hermes"],
                    "desc": "สถาปัตยกรรมแกนกลางของระบบผู้ช่วย AI",
                    "category": "identity"
                }
            ]
        },
        "corrections": {
            "label": "ตารางแก้คำเพี้ยนอัตโนมัติ (Phonetic Corrections)",
            "icon": "🛠️",
            "description": "กฎ Regex และคำแปลกๆ ที่ STT มักได้ยินผิด แปลงกลับเป็นคำที่ถูกต้องทันที",
            "items": [
                {
                    "id": "cor_ac_on",
                    "term": "เปิดแอร์",
                    "pattern": r"(?i)เปิดแอ(?!ร์|\w)",
                    "replace_with": "เปิดแอร์",
                    "desc": "แก้คำว่า 'เปิดแอ' เป็น 'เปิดแอร์'"
                },
                {
                    "id": "cor_ac_off",
                    "term": "ปิดแอร์",
                    "pattern": r"(?i)ปิดแอ(?!ร์|\w)",
                    "replace_with": "ปิดแอร์",
                    "desc": "แก้คำว่า 'ปิดแอ' เป็น 'ปิดแอร์'"
                },
                {
                    "id": "cor_maymint",
                    "term": "มายมิ้นท์",
                    "pattern": r"(?i)(?:มายมิน|มายมิ่น|มายมินท์)(?!ท์)",
                    "replace_with": "มายมิ้นท์",
                    "desc": "แก้ชื่อมายมิ้นท์ที่ไม่มีการันต์"
                },
                {
                    "id": "cor_gmail",
                    "term": "Gmail",
                    "pattern": r"(?i)(?:จีเมล์|จีเมล|เจเมล์|เจเมล)",
                    "replace_with": "Gmail",
                    "desc": "แก้คำว่า Gmail ในภาษาไทย"
                },
                {
                    "id": "cor_drive",
                    "term": "Google Drive",
                    "pattern": r"(?i)(?:กูเกิ้?ลไดร[ฟว์]|กูเกิลไดร[ฟว์]|เกิ้ลไดร[ฟว์])",
                    "replace_with": "Google Drive",
                    "desc": "แก้คำว่า Google Drive"
                },
                {
                    "id": "cor_calendar",
                    "term": "Google Calendar",
                    "pattern": r"(?i)(?:กูเกิ้?ลคาเลนดาร์|คาเลนดาร์)",
                    "replace_with": "Google Calendar",
                    "desc": "แก้คำว่า Google Calendar"
                },
                {
                    "id": "cor_docker",
                    "term": "Docker",
                    "pattern": r"(?i)(?:ด็?อกเกอร์)",
                    "replace_with": "Docker",
                    "desc": "แก้คำว่า Docker"
                },
                {
                    "id": "cor_cloudflare",
                    "term": "Cloudflare",
                    "pattern": r"(?i)(?:คลาวด์แฟล?ร์|คลาวแฟลร์)",
                    "replace_with": "Cloudflare",
                    "desc": "แก้คำว่า Cloudflare"
                },
                {
                    "id": "cor_postgres",
                    "term": "PostgreSQL",
                    "pattern": r"(?i)(?:โพสเกรส|โพสต์เกรส|โพสเกรสคิวแอล)",
                    "replace_with": "PostgreSQL",
                    "desc": "แก้คำว่า PostgreSQL"
                },
                {
                    "id": "cor_mysql",
                    "term": "MySQL",
                    "pattern": r"(?i)(?:มายเอสคิวแอล|มายซีเควล)",
                    "replace_with": "MySQL",
                    "desc": "แก้คำว่า MySQL"
                },
                {
                    "id": "cor_nginx",
                    "term": "NGINX",
                    "pattern": r"(?i)(?:เอนจิ้นเอ็กซ์|เอ็นจินเอ็กซ์|เอนจินเอกซ์)",
                    "replace_with": "NGINX",
                    "desc": "แก้คำว่า NGINX"
                },
                {
                    "id": "cor_github",
                    "term": "GitHub",
                    "pattern": r"(?i)(?:กิตฮับ|กิทฮับ)",
                    "replace_with": "GitHub",
                    "desc": "แก้คำว่า GitHub"
                },
                {
                    "id": "cor_tuya",
                    "term": "Tuya",
                    "pattern": r"(?i)(?:ทูย่า|ทูยา)",
                    "replace_with": "Tuya",
                    "desc": "แก้คำว่า Tuya"
                }
            ]
        }
    }
}


class KnowledgeLexiconManager:
    """Manager for Speech Recognition Lexicon, Command Bank, and Vocabulary Storage."""

    def __init__(self, file_path: Path = LEXICON_FILE_PATH):
        self.file_path = file_path
        self._cache: Optional[Dict[str, Any]] = None
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Ensure knowledge_lexicon.json exists on disk with default values."""
        with _lexicon_lock:
            if not self.file_path.exists():
                try:
                    self.file_path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = self.file_path.with_suffix(".tmp")
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(DEFAULT_LEXICON, f, ensure_ascii=False, indent=2)
                    tmp.replace(self.file_path)
                    logger.info("Initialized default knowledge_lexicon.json at %s", self.file_path)
                except Exception as e:
                    logger.error("Failed to create default knowledge_lexicon.json: %s", e)

    def load(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load lexicon data from disk thread-safely."""
        with _lexicon_lock:
            if self._cache is not None and not force_reload:
                return self._cache

            if self.file_path.exists():
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict) and "categories" in data:
                            self._cache = data
                            return self._cache
                except Exception as e:
                    logger.warning("Error reading %s: %s, falling back to default", self.file_path, e)

            # Fallback
            self._cache = dict(DEFAULT_LEXICON)
            return self._cache

    def save(self, data: Dict[str, Any]) -> bool:
        """Atomically persist lexicon data to disk."""
        with _lexicon_lock:
            try:
                data["updated_at"] = int(time.time())
                tmp = self.file_path.with_suffix(".tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                tmp.replace(self.file_path)
                self._cache = data
                logger.info("Saved knowledge_lexicon.json successfully.")
                return True
            except Exception as e:
                logger.error("Failed to save %s: %s", self.file_path, e)
                return False

    def get_all(self) -> Dict[str, Any]:
        """Retrieve complete lexicon dictionary."""
        return self.load()

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary count of items across all categories."""
        data = self.load()
        cats = data.get("categories", {})
        counts = {cat_id: len(cat_info.get("items", [])) for cat_id, cat_info in cats.items()}
        total_items = sum(counts.values())
        return {
            "total_items": total_items,
            "category_counts": counts,
            "updated_at": data.get("updated_at", 0),
        }

    def add_or_update_item(
        self,
        category: str,
        term: str,
        aliases: Optional[List[str]] = None,
        desc: str = "",
        pattern: str = "",
        replace_with: str = "",
        item_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add or update an item within a category."""
        with _lexicon_lock:
            data = self.load(force_reload=True)
            categories = data.setdefault("categories", {})
            if category not in categories:
                categories[category] = {
                    "label": category.capitalize(),
                    "icon": "📌",
                    "description": f"หมวดหมู่ {category}",
                    "items": []
                }

            items = categories[category].setdefault("items", [])
            target_id = item_id or f"{category[:3]}_{int(time.time() * 1000) % 1000000}"

            # Check if updating existing
            existing_idx = next((i for i, it in enumerate(items) if it.get("id") == target_id), None)
            
            # Clean aliases
            clean_aliases = [a.strip() for a in (aliases or []) if a.strip()]

            new_item = {
                "id": target_id,
                "term": term.strip(),
                "category": category,
                "desc": desc.strip(),
            }
            if clean_aliases:
                new_item["aliases"] = clean_aliases
            if pattern.strip():
                new_item["pattern"] = pattern.strip()
            if replace_with.strip():
                new_item["replace_with"] = replace_with.strip()

            if existing_idx is not None:
                items[existing_idx] = new_item
            else:
                items.append(new_item)

            self.save(data)
            return new_item

    def delete_item(self, category: str, item_id: str) -> bool:
        """Delete an item from a category by item_id."""
        with _lexicon_lock:
            data = self.load(force_reload=True)
            cats = data.get("categories", {})
            if category not in cats:
                return False
            items = cats[category].get("items", [])
            initial_len = len(items)
            cats[category]["items"] = [it for it in items if it.get("id") != item_id]
            if len(cats[category]["items"]) < initial_len:
                self.save(data)
                return True
            return False

    def reset_to_default(self) -> None:
        """Reset lexicon file back to factory defaults."""
        with _lexicon_lock:
            self.save(dict(DEFAULT_LEXICON))
            logger.info("Knowledge lexicon reset to default.")

    # -------------------------------------------------------------------------
    # STT System Prompt Generation (Priming Multimodal Audio Models)
    # -------------------------------------------------------------------------
    def generate_stt_system_prompt(self) -> str:
        """Generate high-density domain knowledge instructions for Gemini STT models.
        
        Injects canonical spellings of devices, workspace tools, tech terms, and names
        to prevent phonetically similar hallucinations without distorting natural conversational intent.
        """
        data = self.load()
        cats = data.get("categories", {})

        dev_terms = [it.get("term") for it in cats.get("devices", {}).get("items", []) if it.get("term")]
        ws_terms = [it.get("term") for it in cats.get("workspace", {}).get("items", []) if it.get("term")]
        tech_terms = [it.get("term") for it in cats.get("technical", {}).get("items", []) if it.get("term")]
        id_terms = [it.get("term") for it in cats.get("identity", {}).get("items", []) if it.get("term")]

        prompt = (
            "ถอดความเสียงภาษาไทยที่ได้ยินออกมาเป็นข้อความตัวอักษรอย่างถูกต้อง แม่นยำ และตรงตามเสียงพูดจริงทุกคำ\n"
            "ข้อกำหนดสำคัญ:\n"
            "1. ถอดความคำพูดอย่างเป็นธรรมชาติ ตรงตามที่ผู้พูดพูดจริง ห้ามสรุปความ ห้ามแต่งเติม และห้ามแปลงเป็นคำสั่งอื่น\n"
            "2. หากมีชื่ออุปกรณ์ ศัพท์เฉพาะทาง หรือชื่อบริการ ให้สะกดตามรูปคำที่ถูกต้อง เช่น "
            f"{', '.join(tech_terms[:6])}, {', '.join(ws_terms[:4])}, {', '.join(dev_terms[:4])}, {', '.join(id_terms[:2])}\n"
            "3. ตอบเฉพาะข้อความที่ได้ยินเท่านั้น ห้ามมีคำอธิบายเพิ่มเติมใดๆ"
        )
        return prompt

    # -------------------------------------------------------------------------
    # Normalization & Misheard Correction Engine
    # -------------------------------------------------------------------------
    def normalize_text(self, text: str) -> Tuple[str, List[Dict[str, str]]]:
        """Normalize transcribed text by correcting common phonetic mishearings.
        
        Applies:
        1. Explicit Regex corrections from the 'corrections' category.
        2. Alias replacements from entity categories (excluding 'commands' to prevent altering conversational user intent).
        
        Returns:
            Tuple[str, List[Dict[str, str]]]: (normalized_text, list_of_applied_corrections)
        """
        if not text:
            return "", []

        normalized = text
        applied: List[Dict[str, str]] = []
        data = self.load()
        cats = data.get("categories", {})

        # Step 1: Run explicit regex rules from 'corrections'
        corrections_items = cats.get("corrections", {}).get("items", [])
        for item in corrections_items:
            pattern_str = item.get("pattern", "")
            replacement = item.get("replace_with", item.get("term", ""))
            if pattern_str and replacement:
                try:
                    new_text, count = re.subn(pattern_str, replacement, normalized)
                    if count > 0:
                        applied.append({
                            "type": "regex_correction",
                            "rule_id": item.get("id", ""),
                            "matched": pattern_str,
                            "replaced_with": replacement,
                            "count": str(count)
                        })
                        normalized = new_text
                except Exception as re_err:
                    logger.debug("Regex error for rule %s: %s", item.get("id"), re_err)

        # Step 2: Run alias-to-canonical term mapping from entity categories
        for cat_key, cat_data in cats.items():
            # CRITICAL: Exclude 'corrections' (handled above) and 'commands' (never replace conversational user sentences with command labels!)
            if cat_key in ("corrections", "commands"):
                continue
            for item in cat_data.get("items", []):
                canonical = item.get("term", "")
                aliases = item.get("aliases", [])
                if not canonical or not aliases:
                    continue
                # Sort aliases by length descending so longer phrases match first
                sorted_aliases = sorted(aliases, key=lambda a: len(a), reverse=True)
                for alias in sorted_aliases:
                    if not alias or alias == canonical:
                        continue
                    
                    # SAFETY GUARD: Ignore short ambiguous Thai words (< 4 chars) to prevent severe collisions
                    # e.g., "แอ" colliding with "แอป", "แอบ"; "มาย" colliding with "มากมาย"
                    if len(alias) < 4 and not alias.isascii():
                        continue

                    # Match exact word boundaries or non-alphanumeric borders
                    if alias in normalized:
                        escaped_alias = re.escape(alias)
                        if canonical.startswith(alias) and len(canonical) > len(alias):
                            suffix = re.escape(canonical[len(alias):])
                            pattern = rf"{escaped_alias}(?!{suffix})"
                        elif canonical.endswith(alias) and len(canonical) > len(alias):
                            prefix = re.escape(canonical[:-len(alias)])
                            pattern = rf"(?<!{prefix}){escaped_alias}"
                        elif alias.isalnum():
                            pattern = rf"(?<![\u0E00-\u0E7Fa-zA-Z0-9]){escaped_alias}(?![\u0E00-\u0E7Fa-zA-Z0-9])"
                        else:
                            pattern = escaped_alias

                        try:
                            new_text, count = re.subn(pattern, canonical, normalized)
                            if count > 0:
                                applied.append({
                                    "type": "alias_normalization",
                                    "category": cat_key,
                                    "alias": alias,
                                    "canonical": canonical,
                                    "count": str(count)
                                })
                                normalized = new_text
                        except Exception:
                            pass

        # Cleanup multiple consecutive spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized, applied

    # -------------------------------------------------------------------------
    # 🤖 Autonomous Vocabulary Learning & Entity Discovery Engine
    # -------------------------------------------------------------------------
    def auto_learn_term(
        self,
        category: str,
        term: str,
        aliases: Optional[List[str]] = None,
        desc: str = "",
        source: str = "auto_learned"
    ) -> Optional[Dict[str, Any]]:
        """Autonomously learn a new term into the lexicon without duplicating."""
        clean_term = term.strip()
        if not clean_term or len(clean_term) < 2:
            return None

        # Filter out common stop words / conversational fillers
        STOP_WORDS = {
            "สวัสดี", "ขอบคุณ", "ครับ", "ค่ะ", "นะคะ", "น้า", "งับ", "วันนี้", "พรุ่งนี้", 
            "เมื่อวาน", "อะไร", "ทำไม", "ยังไง", "อย่างไร", "ไหน", "ที่ไหน", "ใคร", "ช่วย",
            "หน่อย", "ด้วย", "แล้ว", "และ", "หรือ", "ถ้า", "แต่", "ว่า", "กินข้าว", "นอน",
            "ok", "hello", "hi", "yes", "no", "thanks", "thank you"
        }
        if clean_term.lower() in STOP_WORDS:
            return None

        with _lexicon_lock:
            data = self.load(force_reload=True)
            cats = data.setdefault("categories", {})
            if category not in cats:
                category = "commands"

            items = cats[category].setdefault("items", [])

            # Check if term already exists in ANY category
            for cat_k, cat_v in cats.items():
                for it in cat_v.get("items", []):
                    if it.get("term", "").strip().lower() == clean_term.lower():
                        # Already exists! Merge new aliases if any
                        existing_aliases = set(it.get("aliases", []))
                        new_aliases = [a.strip() for a in (aliases or []) if a.strip() and a.strip().lower() not in existing_aliases]
                        if new_aliases:
                            it["aliases"] = list(existing_aliases.union(new_aliases))
                            it["updated_at"] = int(time.time())
                            self.save(data)
                            logger.info("🤖 [Auto-Learning] Merged new aliases into existing term '%s': %s", clean_term, new_aliases)
                            return it
                        return None  # Already present, no changes

            # Create new auto-learned entry
            new_id = f"{category[:3]}_auto_{int(time.time() * 1000) % 1000000}"
            clean_aliases = [a.strip() for a in (aliases or []) if a.strip() and a.strip().lower() != clean_term.lower()]
            new_item = {
                "id": new_id,
                "term": clean_term,
                "category": category,
                "aliases": clean_aliases,
                "desc": desc.strip() or "เรียนรู้และบันทึกอัตโนมัติจากบทสนทนา",
                "source": source,
                "auto_learned": True,
                "created_at": int(time.time())
            }
            items.append(new_item)
            self.save(data)
            logger.info("🤖 [Auto-Learning] Successfully indexed new term: '%s' [%s] with aliases %s", clean_term, category, clean_aliases)
            return new_item

    def extract_and_auto_learn(
        self,
        user_text: str,
        reply_text: str = "",
        tool_events: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Asynchronously analyze conversation and tool interactions to discover and learn novel vocabulary."""
        if not user_text or len(user_text.strip()) < 3:
            return []

        learned_items = []

        # 1. Direct Heuristic Extraction for Common Correction Phrases
        # e.g., "ไม่ใช่ หมายถึง X" หรือ "เรียก X ว่า Y" หรือ "เรียกว่า X"
        correction_match = re.search(r"(?:ไม่ใช่|หมายถึง|เรียกว่า|คือคำว่า)\s+([^\s,.!?]+)", user_text)
        if correction_match:
            cand_term = correction_match.group(1).strip()
            if len(cand_term) >= 2:
                learned = self.auto_learn_term(
                    category="commands",
                    term=cand_term,
                    desc="คำที่ผู้ใช้แก้ไขหรือระบุความหมายโดยตรง",
                    source="correction_heuristic"
                )
                if learned:
                    learned_items.append(learned)

        # 2. Extract Device / Service entities from Tool Events
        if tool_events:
            for ev in tool_events:
                tool_name = ev.get("tool", "")
                args = ev.get("args", {})
                if tool_name.startswith("smart_home_"):
                    dev_name = args.get("device_name") or args.get("device")
                    if dev_name and isinstance(dev_name, str) and len(dev_name) >= 2:
                        learned = self.auto_learn_term(
                            category="devices",
                            term=dev_name,
                            desc=f"อุปกรณ์ Smart Home ที่ตรวจพบจากการทำงาน ({tool_name})",
                            source="smart_home_discovery"
                        )
                        if learned:
                            learned_items.append(learned)
                elif tool_name.startswith("google_workspace_"):
                    title = args.get("title") or args.get("query")
                    if title and isinstance(title, str) and 3 <= len(title) <= 40 and not title.startswith("http"):
                        learned = self.auto_learn_term(
                            category="workspace",
                            term=title,
                            desc=f"ไฟล์/ข้อมูลที่เกี่ยวข้องกับ Google Workspace",
                            source="workspace_discovery"
                        )
                        if learned:
                            learned_items.append(learned)

        # 3. LLM-Powered Autonomous Vocabulary Harvester (Fast Gemini 2.5 Flash query)
        api_key = _resolve_api_key()
        if not api_key:
            return learned_items

        try:
            prompt = (
                "You are an autonomous lexicon discovery system for a Thai personal AI assistant.\n"
                "Analyze user utterance and assistant response.\n"
                "Extract any NEW domain-specific words, technical terms, smart home devices, workspace tools, custom command names, or proper nouns that should be permanently remembered into the STT Lexicon to prevent future speech recognition mistakes.\n"
                "CRITICAL RULES:\n"
                "- DO NOT extract common everyday conversational words, pleasantries, verbs, or stopwords (e.g. สวัสดี, ขอบคุณ, กินข้าว, ทำงาน, ไปไหน, วันนี้, ครับ, ค่ะ, ช่วย, หน่อย, จ้า, จ้ะ).\n"
                "- ONLY extract specialized entities, domain terms, device names, or custom command triggers.\n"
                "- If no new specialized vocabulary is introduced, return an empty array: []\n"
                "- If found, output ONLY a valid JSON array of objects:\n"
                "[{\"category\": \"commands\"|\"devices\"|\"workspace\"|\"technical\"|\"identity\", \"term\": \"...\", \"aliases\": [\"...\"], \"desc\": \"...\"}]"
            )
            payload = {
                "model": "ag/gemini-2.5-flash",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"User: {user_text}\nAssistant: {reply_text}"}
                ],
                "temperature": 0.0,
                "stream": False
            }
            req = urllib.request.Request(
                f"{DEFAULT_GATEWAY_URL}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Hermes/1.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                raw_content = res_data["choices"][0]["message"].get("content", "").strip()

                match = re.search(r"\[[\s\S]*\]", raw_content)
                if match:
                    extracted_list = json.loads(match.group(0))
                    if isinstance(extracted_list, list):
                        for entry in extracted_list:
                            cat = entry.get("category", "commands")
                            term = entry.get("term", "").strip()
                            aliases = entry.get("aliases", [])
                            desc = entry.get("desc", "เรียนรู้อัตโนมัติจากบทสนทนา")
                            if term and len(term) >= 2:
                                learned = self.auto_learn_term(
                                    category=cat,
                                    term=term,
                                    aliases=aliases,
                                    desc=desc,
                                    source="autonomous_ai_harvester"
                                )
                                if learned:
                                    learned_items.append(learned)
        except Exception as harvest_err:
            logger.debug("Autonomous vocabulary harvest failed: %s", harvest_err)

        return learned_items


# Singleton instance
lexicon_mgr = KnowledgeLexiconManager()
