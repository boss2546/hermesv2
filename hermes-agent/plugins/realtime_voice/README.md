# 🎙️ Real-time Voice Chat Plugin for Hermes Agent

ปลั๊กอินสำหรับการสื่อสารและพูดคุยด้วยเสียงแบบเรียลไทม์ (Real-time Speech Synthesis & Voice Interaction) สำหรับ Hermes Agent ขับเคลื่อนด้วยระบบ 9Router Central AI Gateway (`https://api.meuu.club/v1`).

---

## 🌟 ฟีเจอร์เด่น (Key Features)

1. **🎙️ เสียงพูดภาษาไทยธรรมชาติสมบูรณ์ (Neural Thai TTS):**
   * เสียงหญิง: `edge-tts/th-TH-PremwadeeNeural` (เสียงเปรมวดี หวาน นุ่มนวล ชัดเจน)
   * เสียงชาย: `edge-tts/th-TH-NiwatNeural` (เสียงนิวัฒน์ ทรงพลัง เป็นทางการ)
2. **🇺🇸 เสียงภาษาอังกฤษคมชัด:**
   * เสียงหญิง: `edge-tts/en-US-JennyNeural`
   * เสียงชาย: `edge-tts/en-US-GuyNeural`
3. **⚡ รันเสียงทันทีผ่านลำโพงของเครื่อง:**
   * รองรับทั้ง macOS (`afplay`), Linux (`paplay`/`aplay`/`ffplay`), และ Windows
4. **💬 คำสั่ง Slash Command ในตัว (`/voice`):**
   * `/voice say <ข้อความ>` — สั่งให้ Hermes พูดข้อความออกเสียงทันที
   * `/voice status` — ตรวจสอบสถานะและเสียงที่กำลังใช้งาน
   * `/voice set-voice <ชื่อเสียง>` — สลับเสียงพูด (premwadee, niwat, jenny, guy)
   * `/voice auto-speak on|off` — เปิด/ปิดโหมดให้ AI อ่านคำตอบออกเสียงอัตโนมัติ
5. **🔧 Custom Tools สำหรับให้ AI สั่งพูดเอง:**
   * `voice_speak` — เครื่องมือให้ AI สั่งเปล่งเสียงพูดออกมา
   * `voice_status` — ตรวจสอบระบบเสียง

---

## 🚀 วิธีการใช้งาน

### 1. ใช้งานผ่าน Terminal / Chat
```bash
# ตรวจสอบสถานะ
/voice status

# ทดสอบสั่งพูด
/voice say สวัสดีครับบอส มายมิ้นพร้อมคุยแล้วค่ะ

# เปลี่ยนเสียงเป็นเสียงผู้ชาย
/voice set-voice niwat
```

### 2. ให้ AI ใช้เป็นเครื่องมือ
```bash
hermes -z "ช่วยใช้ tool voice_speak พูดว่า 'ยินดีต้อนรับบอสครับ' ให้หน่อย"
```
