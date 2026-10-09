#!/usr/bin/env python3
"""Deep and exhaustive test suite for Google Workspace capabilities.

Tests all services:
1. Gmail (search, get, send test email to self)
2. Drive (create folder, upload, download, search, metadata, delete)
3. Calendar (list, create event, delete event)
4. Docs (create doc, append text, read doc)
5. Sheets (create sheet, append rows, read cells)
"""

from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add plugins to sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = WORKSPACE_ROOT / "hermes-agent" / "plugins"
if str(PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGINS_DIR))

from google_workspace import execute_google_workspace_tool

RESULTS = []

def report(service: str, test_name: str, passed: bool, details: str = ""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {service} -> {test_name}: {details}")
    RESULTS.append({
        "service": service,
        "test": test_name,
        "status": status,
        "details": details
    })


def test_gmail():
    print("\n--- 📧 TESTING GMAIL ---")
    # 1. Search
    res = execute_google_workspace_tool("google_workspace_gmail", {
        "action": "search",
        "query": "newer_than:14d",
        "max_results": 2
    })
    if res.get("success") and isinstance(res.get("data"), list):
        count = len(res["data"])
        report("Gmail", "Search Emails", True, f"Found {count} emails")
        
        # 2. Get body if emails found
        if count > 0:
            mid = res["data"][0]["id"]
            get_res = execute_google_workspace_tool("google_workspace_gmail", {
                "action": "get",
                "message_id": mid
            })
            if get_res.get("success") and "subject" in get_res.get("data", {}):
                subj = get_res["data"]["subject"]
                report("Gmail", "Get Email Content", True, f"Read email: '{subj[:40]}'")
            else:
                report("Gmail", "Get Email Content", False, str(get_res))
    else:
        report("Gmail", "Search Emails", False, str(res))

    # 3. Send test email to Boss
    to_email = "bossok2546@gmail.com"
    send_res = execute_google_workspace_tool("google_workspace_gmail", {
        "action": "send",
        "to": to_email,
        "subject": "💖 [Hermes Auto-Test] น้องมายมิ้นท์ทดสอบส่งอีเมล",
        "body": "สวัสดีค่ะบอส!\n\nนี่คืออีเมลทดสอบอัตโนมัติจากระบบ Hermes & Maymint Voice Assistant ค่ะ ระบบส่งอีเมลผ่าน Gmail API สำเร็จสมบูรณ์ 100% แล้วน้าา!\n\nเวลาทดสอบ: " + time.strftime("%Y-%m-%d %H:%M:%S")
    })
    if send_res.get("success"):
        report("Gmail", "Send Email", True, f"Sent test email to {to_email}")
    else:
        report("Gmail", "Send Email", False, str(send_res))


def test_calendar():
    print("\n--- 📅 TESTING GOOGLE CALENDAR ---")
    # 1. List
    list_res = execute_google_workspace_tool("google_workspace_calendar", {"action": "list"})
    if list_res.get("success"):
        events = list_res.get("data", [])
        report("Calendar", "List Events", True, f"Retrieved {len(events)} events")
    else:
        report("Calendar", "List Events", False, str(list_res))

    # 2. Create Event (tomorrow at 10:00 AM)
    now = datetime.now(timezone(timedelta(hours=7)))
    tomorrow_start = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow_start + timedelta(hours=1)

    create_res = execute_google_workspace_tool("google_workspace_calendar", {
        "action": "create",
        "summary": "🌸 [Hermes Test] Maymint & Boss Standup Meeting",
        "start": tomorrow_start.isoformat(),
        "end": tomorrow_end.isoformat(),
        "location": "Discord / Voice Room"
    })

    event_id = None
    if create_res.get("success"):
        data = create_res.get("data", {})
        event_id = data.get("id")
        report("Calendar", "Create Event", True, f"Created event ID {event_id} at {tomorrow_start.strftime('%d/%m %H:%M')}")
    else:
        report("Calendar", "Create Event", False, str(create_res))

    # 3. Delete Event (Cleanup)
    if event_id:
        del_res = execute_google_workspace_tool("google_workspace_calendar", {
            "action": "delete",
            "event_id": event_id
        })
        if del_res.get("success"):
            report("Calendar", "Delete Event", True, f"Successfully cleaned up event {event_id}")
        else:
            report("Calendar", "Delete Event", False, str(del_res))


def test_drive():
    print("\n--- 📂 TESTING GOOGLE DRIVE ---")
    # 1. Search
    search_res = execute_google_workspace_tool("google_workspace_drive", {
        "action": "search",
        "query": "trashed = false",
        "max_results": 3
    })
    if search_res.get("success"):
        files = search_res.get("data", [])
        report("Drive", "Search Files", True, f"Found {len(files)} files on Drive")
    else:
        report("Drive", "Search Files", False, str(search_res))

    # 2. Create Folder
    folder_name = "Hermes_Test_Vault"
    folder_res = execute_google_workspace_tool("google_workspace_drive", {
        "action": "create_folder",
        "folder_name": folder_name
    })
    folder_id = None
    if folder_res.get("success"):
        folder_id = folder_res.get("data", {}).get("id")
        report("Drive", "Create Folder", True, f"Created folder '{folder_name}' (ID: {folder_id})")
    else:
        report("Drive", "Create Folder", False, str(folder_res))

    # 3. Create local temp file and Upload
    temp_file = WORKSPACE_ROOT / "scratch" / "test_drive_upload.txt"
    temp_file.parent.mkdir(exist_ok=True)
    temp_file.write_text("Hello from Hermes Agent! Test Drive file upload.", encoding="utf-8")

    upload_res = execute_google_workspace_tool("google_workspace_drive", {
        "action": "upload",
        "local_path": str(temp_file)
    })
    uploaded_file_id = None
    if upload_res.get("success"):
        uploaded_file_id = upload_res.get("data", {}).get("id")
        report("Drive", "Upload File", True, f"Uploaded file to Drive (ID: {uploaded_file_id})")
    else:
        report("Drive", "Upload File", False, str(upload_res))

    # 4. Download file back to another location
    if uploaded_file_id:
        down_target = WORKSPACE_ROOT / "scratch" / "test_drive_downloaded.txt"
        down_res = execute_google_workspace_tool("google_workspace_drive", {
            "action": "download",
            "file_id": uploaded_file_id,
            "local_path": str(down_target)
        })
        if down_res.get("success") and down_target.exists():
            content = down_target.read_text(encoding="utf-8")
            report("Drive", "Download File", True, f"Downloaded {len(content)} bytes successfully")
        else:
            report("Drive", "Download File", False, str(down_res))

        # 5. Delete file
        del_res = execute_google_workspace_tool("google_workspace_drive", {
            "action": "delete",
            "file_id": uploaded_file_id,
            "permanent": True
        })
        if del_res.get("success"):
            report("Drive", "Delete File", True, f"Deleted test file {uploaded_file_id}")
        else:
            report("Drive", "Delete File", False, str(del_res))

    # Cleanup folder
    if folder_id:
        execute_google_workspace_tool("google_workspace_drive", {
            "action": "delete",
            "file_id": folder_id,
            "permanent": True
        })


def test_docs_and_sheets():
    print("\n--- 📝 TESTING GOOGLE DOCS & SHEETS ---")
    # 1. Google Docs Create
    doc_res = execute_google_workspace_tool("google_workspace_sheets_docs", {
        "service": "docs",
        "action": "create",
        "title": "🌸 [Hermes Test] Maymint Briefing Document",
        "text": "บันทึกทดสอบระบบ Google Docs จากน้องมายมิ้นท์และบอสค่ะ"
    })
    doc_id = None
    if doc_res.get("success"):
        doc_id = doc_res.get("data", {}).get("documentId")
        report("Docs", "Create Document", True, f"Created Doc (ID: {doc_id})")
    else:
        report("Docs", "Create Document", False, str(doc_res))

    # 2. Google Docs Append
    if doc_id:
        app_res = execute_google_workspace_tool("google_workspace_sheets_docs", {
            "service": "docs",
            "action": "append",
            "id": doc_id,
            "text": "\n\nข้อความต่อท้าย: การทดสอบรอบที่ 2 สำเร็จอย่างราบรื่น!"
        })
        if app_res.get("success"):
            report("Docs", "Append Text", True, "Appended text to document")
        else:
            report("Docs", "Append Text", False, str(app_res))

        # 3. Google Docs Read
        get_doc = execute_google_workspace_tool("google_workspace_sheets_docs", {
            "service": "docs",
            "action": "get",
            "id": doc_id
        })
        if get_doc.get("success"):
            report("Docs", "Read Document", True, "Successfully retrieved full doc content")
        else:
            report("Docs", "Read Document", False, str(get_doc))

        # Cleanup Doc
        execute_google_workspace_tool("google_workspace_drive", {
            "action": "delete",
            "file_id": doc_id,
            "permanent": True
        })

    # 4. Google Sheets Create
    sheet_res = execute_google_workspace_tool("google_workspace_sheets_docs", {
        "service": "sheets",
        "action": "create",
        "title": "🌸 [Hermes Test] Maymint Expense Log"
    })
    sheet_id = None
    if sheet_res.get("success"):
        sheet_id = sheet_res.get("data", {}).get("spreadsheetId")
        report("Sheets", "Create Spreadsheet", True, f"Created Sheet (ID: {sheet_id})")
    else:
        report("Sheets", "Create Spreadsheet", False, str(sheet_res))

    # 5. Google Sheets Update / Append
    if sheet_id:
        update_res = execute_google_workspace_tool("google_workspace_sheets_docs", {
            "service": "sheets",
            "action": "update",
            "id": sheet_id,
            "range": "A1:C2",
            "values": json.dumps([
                ["รายการ", "จำนวนเงิน", "สถานะ"],
                ["กาแฟอเมริกาโน่", "65", "เรียบร้อย"]
            ])
        })
        if update_res.get("success"):
            report("Sheets", "Update Cells", True, "Updated A1:C2 with table headers and row")
        else:
            report("Sheets", "Update Cells", False, str(update_res))

        # 6. Google Sheets Read
        read_res = execute_google_workspace_tool("google_workspace_sheets_docs", {
            "service": "sheets",
            "action": "get",
            "id": sheet_id,
            "range": "A1:C2"
        })
        if read_res.get("success"):
            rows = read_res.get("data", [])
            report("Sheets", "Read Cells", True, f"Read {len(rows)} rows from spreadsheet")
        else:
            report("Sheets", "Read Cells", False, str(read_res))

        # Cleanup Sheet
        execute_google_workspace_tool("google_workspace_drive", {
            "action": "delete",
            "file_id": sheet_id,
            "permanent": True
        })


def main():
    print("=================================================================")
    print("🚀 STARTING EXHAUSTIVE GOOGLE WORKSPACE DEEP TEST SUITE")
    print("=================================================================")
    t0 = time.time()

    test_gmail()
    test_calendar()
    test_drive()
    test_docs_and_sheets()

    duration = round(time.time() - t0, 2)
    passed_count = sum(1 for r in RESULTS if r["status"] == "PASS")
    total_count = len(RESULTS)

    print("\n=================================================================")
    print(f"📊 FINAL RESULTS: {passed_count}/{total_count} PASSED ({duration}s)")
    print("=================================================================")
    for r in RESULTS:
        print(f"[{r['status']}] {r['service']} - {r['test']}: {r['details']}")


if __name__ == "__main__":
    main()
