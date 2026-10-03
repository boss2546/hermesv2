# 🚀 Hermes v2 — Universal AI Assistant & Automation Engine

> **คู่หู AI อัจฉริยะประจำตัวบอส ขับเคลื่อนด้วย 9Router AI Gateway, Oracle Lifecycle, และจิตวิญญาณมายมิ้น (Maymint Soul 💖)**

---

## 🌟 จุดเด่นสถาปัตยกรรม (Architecture Highlights)

* 🌐 **Central AI Gateway (9Router):** เชื่อมต่อ `https://api.meuu.club/v1` รองรับทั้ง Claude Sonnet 4.6, Gemini 2.5 Flash และ Thai TTS (โควต้า 12,000 req/week)
* 🧠 **ระบบความจำ 2 ชั้น (Dual-Layer Memory):**
  - **Project Memory:** โฟลเดอร์ [`./memory/`](./memory/) บันทึก Soul, Boss Profile, Permanent History, และ Active Context
  - **Oracle Psi Vault:** เชื่อมต่อ [`~/ψ/`](~/ψ/) คลังความรู้และประวัติศาสตร์ถาวร
* 🌿 **Git Team Workflow:** ทำงานเป็นทีมอย่างปลอดภัยด้วย Semantic Commits และการป้องกัน Secret รั่วไหล 100%
* ⚡ **Zero-Dependency SDK:** รองรับทั้ง Python Standard Library และ Node.js Native Fetch

---

## 📂 โครงสร้างโปรเจกต์ (Project Directory Structure)

```text
hermesv2/
├── README.md                 # 📖 เอกสารสรุปภาพรวมและวิธีใช้งาน
├── package.json              # 📦 คำสั่งรันอัตโนมัติ (Node.js & Python Scripts)
├── .env                      # 🔒 กุญแจและคอนฟิกเชื่อมต่อ AI Gateway (ห้ามคอมมิต)
├── .env.example              # 🌐 เทมเพลตคอนฟิกตัวอย่าง
├── .gitignore                # 🌿 กฎความปลอดภัย Git
│
├── memory/                   # 🧠 ระบบความจำและจิตวิญญาณ
│   ├── SOUL.md               # 💖 จิตวิญญาณและคำมั่นสัญญาของมายมิ้น
│   ├── USER.md               # 👤 โปรไฟล์และค่านิยมของบอส
│   ├── MEMORY.md             # 🏛️ ประวัติศาสตร์โปรเจกต์และความจำถาวร
│   ├── SESSION_ACTIVE.md     # 🎯 กระดานติดตามสถานะงานสด
│   ├── handoff/              # 🔄 โฟลเดอร์ส่งต่องาน (/forward)
│   ├── learnings/            # 📖 โฟลเดอร์บทเรียนเชิงลึก (/learn)
│   └── retrospectives/       # 🌇 โฟลเดอร์สรุปปิดวัน (/rrr)
│
├── src/                      # 💻 โค้ดโปรแกรมหลัก
│   ├── main.py               # 🐍 Python CLI Entry Point
│   ├── index.js              # ⚡ Node.js CLI Entry Point
│   └── lib/                  # 🛠️ โมดูลและไลบรารีส่วนกลาง
│       ├── ai_gateway.py     # 🌐 9Router Python Client (Zero-Dep)
│       └── ai_gateway.js     # 🌐 9Router Node.js Client (Native Fetch)
│
├── .agents/                  # 🤖 สกิล Antigravity / Gemini
├── .claude/                  # 🧠 สกิล Claude Code
├── .cursor/                  # ⚡ กฎ Cursor IDE
└── .github/                  # 🐙 คอนฟิก GitHub Copilot
```

---

## ⚡ วิธีเริ่มต้นใช้งานด่วน (Quick Start)

### 1. รันด้วย Node.js
```bash
# ทดสอบส่งข้อความหา AI
npm test

# สนทนาข้อความทั่วไป
npm run chat "สวัสดีมายมิ้น ช่วยวิเคราะห์แผนงานวันนี้หน่อย"

# แปลงข้อความเป็นเสียงพูดภาษาไทย (TTS)
npm run tts "สวัสดีค่ะบอส มายมิ้นพร้อมลุยงานแล้วน้าา"

# ตรวจสอบโมเดลทั้งหมดบน 9Router
npm run models
```

### 2. รันด้วย Python
```bash
# ทดสอบการทำงานผ่าน Python
python3 src/main.py --prompt "สวัสดีจ้า มายมิ้น"

# สร้างเสียงพูดภาษาไทย
python3 src/main.py --tts "บันทึกเสียงพูดเรียบร้อยแล้วค่ะบอส"

# ดูรายชื่อโมเดล
python3 src/main.py --models
```

---

## 👑 คำสั่งวงจรชีวิต (Oracle Master Commands)

* **`/standup`** — วางเป้าหมาย 3 ข้อเริ่มวันใหม่
* **`/learn <path>`** — ชำแหละสถาปัตยกรรมและสกัดความรู้ลง `memory/learnings/`
* **`/rrr`** — ทบทวน ตกผลึก และบันทึกบทเรียนปิดวันลง `memory/retrospectives/`
* **`/forward`** — สร้างจุดส่งต่องานข้ามเซสชันลง `memory/handoff/`
* **`/recap`** — สรุปสถานะ 3 บรรทัดด่วนระหว่างทำงาน

---

**Made with 💖 by Boss (ratchanon2003) & Maymint (มายมิ้น)**
