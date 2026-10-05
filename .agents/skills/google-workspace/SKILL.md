---
name: google-workspace
description: "ระบบเชื่อมต่อและจัดการ Google Workspace (Gmail, Google Drive, Calendar, Docs, Sheets) สำหรับน้องมายมิ้นท์และบอส"
version: 1.0.0
---

# 🌐 Google Workspace Integration Guide (Maymint & Boss)

มาตรฐานและแนวทางการทำงานร่วมกับบริการ Google Workspace ของบอส (`bossok2546@gmail.com`) ผ่านปลั๊กอิน `hermes-agent/plugins/google_workspace/`

## 🛠️ เครื่องมือที่พร้อมใช้งาน (Available Tools)
1. **`google_workspace_gmail`**:
   - `action="search"`: ค้นหาอีเมล (เช่น `is:unread`, `from:...`, `newer_than:7d`)
   - `action="get"`: อ่านเนื้อหาอีเมลตัวเต็มตาม `message_id`
   - `action="send"`: ส่งอีเมลใหม่ (ระบุ `to`, `subject`, `body`)
   - `action="reply"`: ตอบกลับอีเมลเดิมแบบ Threaded Reply
   - `action="modify"`: ย้ายลงถังขยะ (`add_labels="TRASH"`) หรือเปลี่ยนสถานะอ่านแล้ว/ยังไม่ได้อ่าน

2. **`google_workspace_drive`**:
   - `action="search"`: ค้นหาไฟล์ใน Google Drive
   - `action="get"`: ดูรายละเอียด Metadata และลิงก์เปิดไฟล์
   - `action="upload"`: อัปโหลดไฟล์จากเครื่องคอมบอสขึ้น Drive
   - `action="download"`: ดาวน์โหลดไฟล์ลงมาเก็บในเครื่อง
   - `action="create_folder"`: สั่งสร้างโฟลเดอร์ใหม่
   - `action="share"`: แชร์ไฟล์ให้ผู้อื่น (`role="reader"` หรือ `"writer"`)
   - `action="delete"`: ย้ายลงถังขยะ หรือลบถาวร (`permanent=True`)

3. **`google_workspace_calendar`**:
   - `action="list"`: ดึงรายการนัดหมายและตารางงาน
   - `action="create"`: สร้างนัดหมายใหม่ (ระบุ `summary`, `start`, `end`, `location`)
   - `action="delete"`: ลบนัดหมาย

4. **`google_workspace_sheets_docs`**:
   - `service="sheets"`: อ่านข้อมูลตาราง (`get`), เพิ่มแถว (`append`), แก้ไขช่องเซลล์ (`update`)
   - `service="docs"`: อ่านเอกสาร (`get`), สร้างเอกสาร (`create`), เขียนต่อท้าย (`append`)

## 💖 สไตล์การสนทนาและการตอบของน้องมายมิ้นท์ (Conversation Guidelines)
- สรุปเนื้อหาสำคัญให้อบอุ่น เข้าใจง่าย กระชับ และตรงประเด็น
- กฎ **No-Emoji** สำหรับเสียงพูด (TTS) ยังคงบังคับใช้อย่างเคร่งครัด
- สำหรับการส่งอีเมลหรือลบไฟล์สำคัญ หากบอสไม่ได้สั่งชัดเจน ให้ทวนความถูกต้องกับบอสก่อนเสมอ
