# 🧩 คู่มือการสร้างและพัฒนาปลั๊กอิน (Hermes Plugin Development Guide)

## 🌟 1. สถาปัตยกรรมปลั๊กอินใน Hermes Agent

ปลั๊กอิน (Plugin) คือส่วนขยายระดับโครงสร้างระบบที่สามารถเพิ่มพลังให้ Hermes ได้ 4 มิติพร้อมกัน:
1. **🪝 Lifecycle Hooks:** ดักจับเหตุการณ์ก่อน-หลังรัน Tool หรือตอนเริ่ม-จบ Session
2. **⚡ Slash Commands:** สร้างคำสั่งพิมพ์คุยแบบขึ้นต้นด้วย `/` (เช่น `/template-cmd`)
3. **🔧 Custom Tools:** ฝังเครื่องมือเรียกใช้ฟังก์ชันเฉพาะทางเข้าสู่ระบบ
4. **💾 Memory & Model Providers:** ออกแบบระบบความจำหรือโมเดล AI เฉพาะทาง

---

## 📂 2. โครงสร้างโฟลเดอร์แม่แบบ (Template Layout)

มายสร้างแม่แบบไว้ให้ที่: [hermes-agent/plugins/_template_plugin/](file:///Users/meuu/Desktop/รวมโปรเจ็ค/hermesv2/hermes-agent/plugins/_template_plugin/)

```text
plugins/_template_plugin/
├── plugin.yaml       # 📋 สเปกของปลั๊กอิน (Manifest)
├── __init__.py       # 🔌 จุดลงทะเบียนหลัก (register(ctx))
├── plugin_logic.py   # 🧠 ตรรกะการทำงานจริง, Tool Schemas, และ Handlers
└── README.md         # 📖 คู่มือการติดตั้งและใช้งาน
```

---

## ⚡ 3. ขั้นตอนการสร้างปลั๊กอินใหม่ใน 3 สเต็ป

### ขั้นตอนที่ 1: คัดลอกโฟลเดอร์แม่แบบ
```bash
cp -r hermes-agent/plugins/_template_plugin hermes-agent/plugins/my-new-plugin
```

### ขั้นตอนที่ 2: ปรับแต่งสเปกและโค้ด
1. แก้ไข `plugin.yaml` (ตั้งชื่อ, เวอร์ชั่น, คำอธิบาย, กำหนด hooks ที่ต้องการ)
2. แก้ไข `plugin_logic.py` (ใส่ Business logic, Schema, และ Function Handler)
3. แก้ไข `__init__.py` (ลงทะเบียน Hook, Command, หรือ Tool ผ่าน `ctx`)

### ขั้นตอนที่ 3: ทดสอบและปล่อยใช้งาน (Auto-Discovery)
Hermes จะสแกนและโหลดปลั๊กอินใหม่อัตโนมัติทันที สามารถทดสอบผ่าน Terminal หรือ Web Dashboard:
```bash
# ทดสอบคำสั่ง Slash Command
/my-new-plugin status

# ทดสอบรันผ่าน One-shot CLI
hermes -z "ลองเรียกใช้ custom tool จากปลั๊กอินของฉันหน่อย"
```

---

## 🌐 4. การแชร์และติดตั้งปลั๊กอินผ่าน GitHub
เมื่อบอสสร้างเป็น GitHub Repository (เช่น `boss2546/hermes-plugin-notify`) ทุกคนสามารถสั่งติดตั้งได้ทันที:
```bash
hermes plugins install boss2546/hermes-plugin-notify
```
