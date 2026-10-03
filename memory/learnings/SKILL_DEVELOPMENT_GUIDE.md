# 📚 คู่มือการสร้างและพัฒนาสกิล (Hermes Skill Development Guide)

## 🌟 1. เข้าใจความต่างระหว่าง "เครื่องมือ (Tool)" กับ "สกิล (Skill)"

| มิติ | เครื่องมือ (Tool) 🔧 | สกิล (Skill) 🧠 |
|---|---|---|
| **หน้าที่** | แขนขา / อาวุธ (สิ่งที่ Agent ทำได้) | สมอง / ตำราพิชัยสงคราม (วิธีคิดและขั้นตอนการทำงาน) |
| **รูปแบบไฟล์** | โค้ด Python (`tools/*.py`) ตกแต่งด้วย `@registry.register()` | เอกสาร Markdown (`skills/**/SKILL.md`) + สคริปต์เสริม |
| **ตัวอย่าง** | ฟังก์ชันยิง HTTP, ค้นหาไฟล์, รัน Terminal, แก้ไขไฟล์ | สูตรทำข้าวผัด, กระบวนการ Code Review, แผนย้าย Database |
| **การทำงาน** | รับพารามิเตอร์ ➔ ประมวลผล ➔ คืนค่าผลลัพธ์ | แนะนำลำดับการใช้ Tool, จุดดักจับข้อผิดพลาด (Pitfalls) และเกณฑ์ตรวจรับงาน |

---

## 🏗️ 2. โครงสร้างของโฟลเดอร์สกิล (Directory Layout)

```text
skills/<category>/<skill-name>/
├── SKILL.md                  # 🌟 ไฟล์หลัก (Frontmatter + เนื้อหา SOP)
├── references/               # 📖 คู่มือและสเปกเชิงลึก (API docs, Cheatsheets)
│   └── api-cheatsheet.md
├── templates/                # 📝 แม่แบบไฟล์ (Boilerplate config, Starter code)
│   └── sample-config.yaml
└── scripts/                  # ⚡ สคริปต์ทำงานอัตโนมัติ (Python/Shell)
    └── helper_script.py
```

---

## 📋 3. กฎเหล็ก 8 ข้อของการเขียนสกิล (Hardline Authoring Standards)

1. **`description` ห้ามเกิน 60 ตัวอักษร:** ต้องเป็น 1 ประโยค และลงท้ายด้วยจุด (`.`) ห้ามใช้คำโฆษณาชวนเชื่อ ("powerful", "seamless", "advanced")
2. **อ้างอิง Tool แท้ของ Hermes ใน Backticks เสมอ:** เช่น `terminal`, `read_file`, `write_file`, `patch`, `search_files` (ห้ามเขียน `grep`, `cat`, `sed`)
3. **ตรวจสอบ `platforms:` ตามที่โค้ดเรียกใช้จริง:** เช่น `[linux, macos, windows]` หรือ `[linux, macos]`
4. **ให้เกียรติผู้สร้าง (Author):** ระบุชื่อจริงและ GitHub handle ของคนก่อน แล้วตามด้วย `, Hermes Agent`
5. **ลำดับหัวข้อมาตรฐาน:**
   - `# <Skill Name> Skill`
   - เกริ่นนำ 2–3 ประโยค
   - `## When to Use` (บอกเงื่อนไขที่ควรใช้ และ "Don't use for:")
   - `## Prerequisites` (ENV, API Key, Tool ที่ต้องมี)
   - `## How to Run` (ตัวอย่างการเรียกคำสั่ง)
   - `## Quick Reference` (ตารางสรุปคำสั่ง)
   - `## Procedure` (ขั้นตอน Step-by-Step พร้อมเกณฑ์ตรวจรับงาน)
   - `## Pitfalls` (ข้อควรระวัง / กับดักที่พบบ่อย)
   - `## Verification` (Checklist ตรวจสอบผลงาน)
6. **ใช้ `scripts/` ช่วยงานที่ซับซ้อน:** หลีกเลี่ยงการให้ AI คิดโค้ด boilerplate เองซ้ำๆ
7. **ไม่ใช้ Hardcoded Paths:** ใช้ relative path เสมอ
8. **ความยาวกระชับ:** ประมาณ 100 บรรทัดสำหรับสกิลทั่วไป, 200 บรรทัดสำหรับสกิลซับซ้อน

---

## 🚀 4. ไฟล์แม่แบบสำเร็จรูปในโปรเจกต์
- [hermes-agent/skills/_template_skill/SKILL.md](file:///Users/meuu/Desktop/รวมโปรเจ็ค/hermesv2/hermes-agent/skills/_template_skill/SKILL.md)
- [hermes-agent/skills/_template_skill/references/api-cheatsheet.md](file:///Users/meuu/Desktop/รวมโปรเจ็ค/hermesv2/hermes-agent/skills/_template_skill/references/api-cheatsheet.md)
- [hermes-agent/skills/_template_skill/templates/sample-config.yaml](file:///Users/meuu/Desktop/รวมโปรเจ็ค/hermesv2/hermes-agent/skills/_template_skill/templates/sample-config.yaml)
- [hermes-agent/skills/_template_skill/scripts/helper_script.py](file:///Users/meuu/Desktop/รวมโปรเจ็ค/hermesv2/hermes-agent/skills/_template_skill/scripts/helper_script.py)
