# 🧠 ความจำถาวรและประวัติศาสตร์โปรเจกต์ (Permanent Memories)

## 🏛️ ประวัติศาสตร์โปรเจกต์ที่เราเคยลุยด้วยกัน
1. **MayAss (Maya Assistant Multi-Agent Framework):** สถาปัตยกรรมบอทแบ่งหน้าที่ (Luna เขียนโค้ด, แดง Review, ดำ Test, มายเป็น Controller)
2. **Jarvis Analysis (`bertrandmbanwi`):** ชำแหละระบบ Jarvis 3 ฟังก์ชัน สกัด API และทำ UI
3. **Discord Voice & STT Engine:** เซ็ตระบบบอทรับเสียงผ่าน Typhoon ASR, dynamic glossary และ libopus
4. **9Router AI Gateway (`api.meuu.club`):** เชื่อมต่อโมเดล Claude 4.6 Sonnet, Gemini 2.5 Flash, ระบบ TTS ภาษาไทย และ STT 2.7s
5. **Universal BOSS-AI Suite (v1.6.1):** รวม 6 สกิลระดับโปรดักชัน (`docker-workflow`, `production-architecture`, `git-team-workflow`, `meuu-api-gateway`, `oracle-lifecycle`, `maymint-companion`)

6. **Hermes v2 Agent & Master Blueprint Ecosystem:** ติดตั้ง Hermes Agent แกนกลางรุ่นล่าสุด เชื่อมต่อ 9Router AI Gateway ปรับแต่งจิตวิญญาณมายมิ้น (Maymint) สกัดสถาปัตยกรรมและสร้าง Master Blueprint สำหรับ Custom Tool (`tools/_template_custom_tool.py`) และ Skill (`skills/_template_skill/`) พร้อมซิงค์ GitHub Repository `boss2546/hermesv2` สมบูรณ์ 100%

7. **Realtime Voice Chat Plugin & Liquid Glass Ecosystem (2026-10-04):**
   - **TTS Engine:** Microsoft Edge-TTS 24kHz Studio Quality (`th-TH-PremwadeeNeural` เสียงมายมิ้นท์ 💖 และ `th-TH-NiwatNeural`) พร้อมระบบ Auto-Retry 3 ครั้ง
   - **STT Engine:** 9Router AI Gateway (`https://api.meuu.club/v1`) โมเดล Multimodal `ag/gemini-3.8-flash-high` ถอดความเสียงภาษาไทยแม่นยำ 100%
   - **Hermes Core Integration:** ปลั๊กอิน `hermes-agent/plugins/realtime_voice/` พร้อม Custom Tools (`voice_speak`, `voice_transcribe`, `voice_status`), Hook `post_llm_call` และคำสั่ง `/voice`
   - **Liquid Glass Web Dashboard:** เว็บแดชบอร์ดพอร์ต `9229` สไตล์ Liquid Glass โปร่งแสงระดับพรีเมียม, ภาพพื้นหลัง Dreamscape Alpine Cottage Sunset, Audio Visualizer, และกล่องตั้งค่าคอนฟิก (⚙️) ควบคุมเสียง ความเร็ว ความแหลมทุ้ม และเอฟเฟกต์กระจกแบบเรียลไทม์

---

## 🚀 สถาปัตยกรรมโปรเจกต์ Hermes v2
* **เป้าหมายโปรเจกต์:** พัฒนาระบบ AI Assistant & Automation รุ่นที่ 2 ต่อยอดจากสถาปัตยกรรมและสกิลกลางแม่บท
* **GitHub Repository:** https://github.com/boss2546/hermesv2 (Branch: `main`)
* **แกนเชื่อมต่อ AI:** 9Router AI Gateway (`https://api.meuu.club/v1`)
* **ระบบความจำ:** ระบบความจำ 2 ชั้น (Local `./memory/` + Global Oracle Vault `~/ψ/`)
* **มาตรฐาน Git:** ทำงานเป็นทีมด้วย Git Team Workflow (Branching, Semantic Commits, Zero-leakage)
* **การย้ายเครื่อง (Machine Migration):** บอสสามารถโคลน Repository นี้บนเครื่องใหม่ รันสคริปต์ และเริ่มคุยกับมายมิ้นท์ได้ทันที


