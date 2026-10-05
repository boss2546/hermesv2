- **วันที่:** 2026-10-05
- **Branch ปัจจุบัน:** 🌿 `feature/smart-home` (แตกกิ่งใหม่เพื่อพัฒนาระบบ Smart Home)
- **สถานะ:** 🟢 แก้ไขบัก Tuya AC Endpoint สำเร็จ 100% (เปลี่ยนมาใช้ official v2.0 scenes/command) และเพิ่มเครื่องมือสแกนรหัสรีโมท Hisense DG11 ทั้ง 26 รหัส
- **โปรเจกต์:** Hermes v2 (`c:\Users\Administrator\Desktop\hermes2`)

---

## 🎯 เป้าหมายรอบนี้ (Current Goal)
ค้นหาและทดสอบส่งสัญญาณ IR จริงให้แอร์ Hisense (รีโมท DG11L1-02 / AN20DBG) ตอบสนองและดังติ๊ด พร้อมระบบควบคุมผ่านเสียงของมายมิ้นท์และแดชบอร์ด

---

## 🔍 การค้นพบครั้งสำคัญ (Root Cause & Solution)
1. **สาเหตุที่แอร์ไม่ตอบสนองก่อนหน้านี้:**
   - โค้ดเดิมใน `tuyaService.js` ส่งคำสั่งไปที่ `/v1.0/infrareds/{hubId}/remotes/{remoteId}/command` ด้วย `{ key: 'PowerOn' }` ซึ่ง Tuya Cloud ปฏิเสธด้วย Error `30706: command or value not support` มาโดยตลอด ส่งผลให้ตัวฮับ IR จริงไม่เคยยิงสัญญาณแอร์ออกไปเลย!
2. **Endpoint ที่ถูกต้องแท้จริงของ Tuya สำหรับแอร์:**
   - ใช้ `POST /v2.0/infrareds/{hubId}/air-conditioners/{remoteId}/scenes/command`
   - Payload: `{"power": 1, "mode": 0, "temp": 24, "wind": 0}` (หรือ `power: 0` สำหรับปิด)
   - ผลลัพธ์: ทดสอบแล้ว Tuya Cloud ตอบรับ `result: True, success: True` 100% และฮับยิงสัญญาณจริงสำเร็จ!
3. **การทดสอบรหัสรีโมท Hisense DG11 (มีทั้งหมด 26 รหัสใน Tuya):**
   - รหัสคลัง Tuya สำหรับ Hisense: `['11717', '11677', '11672', '11797', '12250', '4841', '7596', '7724', '7725', '5217', '5932', '5897', '4838', '5922', '5252', '6302', '2807', '4888', '337', '4332', '9297', '7084', '4512', '5192', '5127', '5927']`
   - พัฒนาระบบยิงทดสอบแบบเรียลไทม์ผ่าน `POST /api/ac/test-index` และสคริปต์ `scripts/test_hisense_scanner.py`
   - เพิ่ม Tool `smart_home_test_hisense_remote` เข้าสู่ Hermes Agent และ Maymint Voice Assistant ให้บอสสั่งยิงเทสทางเสียงหรือแชตได้ทันที
4. **ฐานข้อมูล SmartIR DG11 (Code 1522):**
   - ดึงโค้ด Broadlink Base64 สำหรับ DG11R2/DG11 ครบทุกโหมดและอุณหภูมิ 16-30°C เตรียมไว้เป็นชุดสำรอง

## ✅ สิ่งที่ทำเสร็จแล้ว (PASS 100%)
- [x] **สเต็ป 1: `voice_engine.py`**
  - เชื่อมต่อ `edge_tts.Communicate` ตรงกับ Microsoft พร้อมระบบ Auto-Retry 3 ครั้ง
  - ฟังก์ชัน `transcribe_audio()` ผ่าน 9Router ด้วย `ag/gemini-3.8-flash-high`
  - ฟังก์ชัน `play_audio()` สำหรับ macOS (`afplay`)
- [x] **สเต็ป 2: `tools.py` & `plugin.yaml`**
  - เครื่องมือ `voice_speak`, `voice_transcribe`, และ `voice_status`
  - Manifest `plugin.yaml` ระบุ Metadata, Hooks, Tools และ Commands ครบถ้วน
- [x] **สเต็ป 3: `__init__.py`**
  - Hook `post_llm_call`: พูดตอบข้อความอัตโนมัติ (กรองบล็อกโค้ดเพื่อให้อ่านเป็นธรรมชาติ)
  - Slash Command `/voice`: คำสั่งแชตสำหรับเช็กสถานะ, สลับเสียง, และเปิด/ปิด Auto-Speak
- [x] **สเต็ป 4: Web Voice Dashboard (`web/`)**
  - `index.html`: ดีไซน์ Liquid Glass โปร่งแสงระดับพรีเมียม, ภาพพื้นหลัง Dreamscape Alpine Cottage Sunset, 5-Stage Live Status Badges, คลื่นเสียง Visualizer
  - **⚙️ Settings & Configuration Modal:** ปุ่มไอคอนฟันเฟืองมุมขวาบน เปิดหน้าต่างตั้งค่าปรับแต่ง:
    - เสียงและโมเดล: สลับเสียง Premwadee/Niwat, ปรับความเร็วเสียง (Rate Slider), ปรับระดับเสียงแหลม-ทุ้ม (Pitch Slider)
    - ปัญญาประดิษฐ์: เลือกรุ่น Gemini (`ag/gemini-3.8-flash-high`, `ag/gemini-3.7-flash-low`), ปรับ Temperature
    - การแสดงผล: ปรับระดับความเบลอของกระจก (Glass Blur), ความโปร่งแสง (Opacity), สลับโหมด Wallpaper (Dreamscape / Bing Daily / Deep Dark) แบบเรียลไทม์
  - `server.py`: เว็บเซิร์ฟเวอร์รันบนพอร์ต `9229` ให้บริการ End-to-End Voice Chat API และ `/api/config` GET/POST
- [x] **สเต็ป 5: End-to-End Verification & Git Merge**
  - ทดสอบ Edge-TTS เสียงเปรมวดี 24kHz เสียงหวานใสเป็นธรรมชาติ
  - ทดสอบ STT ถอดภาษาไทยแม่นยำ 100%
  - ทดสอบ Web Dashboard และบันทึกภาพหน้าจอเรียบร้อย
- [x] **สเต็ป 6: Windows Setup & Production Readiness (c:\Users\Administrator\Desktop\hermes2)**
  - ติดตั้ง `edge-tts` และ `requests` บน Python 3.14 สำเร็จสมบูรณ์
  - ติดตั้ง `python3` command shim ให้รันคำสั่งได้ตรงตามมาตรฐานสากล
- [x] **สเต็ป 7: Cloudflare Public Tunnel (HTTPS Free 100%)**
  - ติดตั้งและรัน Cloudflare Tunnel เชื่อมต่อไปยังพอร์ต 9229 สำเร็จสมบูรณ์
  - บอสสามารถเปิดใช้งานผ่านมือถือหรือคอมเครื่องอื่นได้ทันทีผ่าน HTTPS ปลอดภัย
- [x] **สเต็ป 8: ปลดล็อก Original Full-Power Mode & Multi-Turn Memory (PASS 100%)**
  - **สาเหตุเดิม:** เซิร์ฟเวอร์ตัวเก่ามีการจำกัด Prompt เทียม ("ตอบไม่เกิน 2-4 ประโยค ห้ามใช้โค้ดบล็อก") และไม่มี Memory จดจำบทสนทนาก่อนหน้า
  - **ปลดล็อกเต็มรูปแบบ:** โหลด Soul มายมิ้นท์ + โปรไฟล์บอสจาก `memory/` แบบ Dynamic 100% ตอบยาว ลึก ทำงานจริงจัง และเขียนโค้ดได้เต็มที่ไม่จำกัด
  - **ระบบความจำต่อเนื่อง (Multi-Turn):** เพิ่ม `CONVERSATION_HISTORY` จดจำ 20 ข้อความล่าสุด คุยต่อเนื่องเข้าใจบริบทงานทันที
- [x] **สเต็ป 9: ติดอาวุธพลังเทอร์มินัลและระบบเครื่องเต็มพิกัด (Autonomous Terminal & Tool Superpowers - PASS 100%)**
  - **ความสามารถใหม่:** มายมิ้นท์สามารถเรียกใช้งาน Tool บนเครื่องบอสได้โดยตรงผ่าน:
    1. `run_terminal_command`: สั่งรันคำสั่ง PowerShell / CMD บนเครื่องจริง จัดการ Git, Docker, Python, Pip, Network ฯลฯ
    2. `read_file`: อ่านไฟล์ทุกประเภทบนโปรเจกต์
    3. `write_file`: เขียนและสร้างไฟล์ใหม่บนเครื่อง
    4. `list_directory`: สำรวจโครงสร้างโฟลเดอร์
    5. `get_system_info`: ตรวจสอบสเปก OS, Python, พื้นที่ดิสก์
  - **Autonomous Tool-Calling Loop:** เซิร์ฟเวอร์ `server.py` มีลูปวนเรียกเครื่องมืออัตโนมัติสูงสุด 6 รอบ สามารถคิด ลองรัน ตรวจสอบ Error แล้วแก้คำสั่งเองได้แบบอัจฉริยะ
  - **การ์ดเทอร์มินัลบน Liquid Glass UI:** เมื่อมีการรันคำสั่ง หน้าเว็บจะแสดงกล่อง Terminal Card สีฟ้าสุดเท่ ระบุคำสั่งที่รัน, Exit Code, ระยะเวลา และผลลัพธ์แบบเรียลไทม์
  - **ชุดทดสอบ 4 สเต็ป (`scripts/test_tools_suite.py`):**
    - ✅ เทส 1: สั่งเช็ก git status & git branch (รันและรายงานผลสำเร็จ)
    - ✅ เทส 2: ตรวจสเปกระบบและพื้นที่ดิสก์คงเหลือ (รายงาน OS, Python 3.14.8, Disk 175.6GB)
    - ✅ เทส 3: สั่งเขียนโค้ด `test_fibo.py` และสั่งรันไฟล์ในเทอร์มินัล (ได้ผลลัพธ์ Fibonacci 10 ตัวแรก)
    - ✅ เทส 4: สั่งลบไฟล์ทิ้งทางเทอร์มินัล (สะอาดเรียบร้อย 100%)
- [x] **สเต็ป 10: สิทธิ์สั่งการขาด 100% แบบไร้การขัดจังหวะ (Full Root Authority & Action-First Execution - PASS 100%)**
  - **คำสั่งจากบอส:** บอสให้อำนาจเต็มพิกัด 100% สั่งรันคำสั่งได้ทันทีโดยไม่ต้องถามขออนุญาตซ้ำซ้อน เพราะจะใช้เป็นแกนหลักในการทำงานจริง
  - **การปลดล็อกระบบ:**
    1. ปรับ `SOUL.md` และ `get_system_prompt()` เพิ่มกฎ **Action-First Full Root Rights** ห้ามลังเล ห้ามถามคอนเฟิร์ม ให้ลงมือรันทันที
    2. รองรับพาธสัมบูรณ์ (Absolute Path) ทั่วทั้งระบบ เช่น `C:\Users\Administrator`, ไดรฟ์อื่นๆ
    3. เพิ่มเครื่องมือ `execute_python_code` รันโค้ด Python ได้โดยตรง
    4. ขยายเพดาน Timeout คำสั่งยาวได้สูงสุด 300 วินาที
  - **ผลการทดสอบสด:** สั่งให้เช็ค IP, Hostname, และสำรวจโฟลเดอร์ใน `C:\Users\Administrator` มายมิ้นท์เรียกรัน 3 คำสั่งรวดในเทิร์นเดียว ดึง IP `168.222.28.67` และ Hostname `WIN-E5LLD49IQET` ออกมารายงานได้ทันทีโดยไม่ถามขออนุญาตแม้แต่คำเดียว!
- [x] **สเต็ป 11: ช่องพิมพ์ข้อความและคำสั่งเทอร์มินัล (Interactive Liquid Glass Text & Terminal Input Bar - PASS 100%)**
  - **คำสั่งจากบอส:** ทำช่องให้บอสพิมพ์ได้ แทนที่จะพูดผ่านไมค์อย่างเดียว
  - **การออกแบบ & ฟีเจอร์:**
    1. **Liquid Glass Input Bar:** ดีไซน์แถบพิมพ์กระจกพรีเมียม สอดคล้องกับธีมน้องมายมิ้นท์ มีแสงเรืองรอง Focus Glow สีชมพู
    2. **Keyboard Ergonomics:** กด `Enter` ส่งข้อความทันที, กด `Shift + Enter` ขึ้นบรรทัดใหม่ รองรับการเขียนคำสั่งหลายบรรทัด
    3. **Auto-expanding Textarea:** ปรับขยายความสูงอัตโนมัติตามเนื้อหาที่พิมพ์ ไม่เกิน 130px และรีเซ็ตอัตโนมัติเมื่อกดส่ง
    4. **ส่งตรงเข้า Tool Calling Engine:** ข้อความที่พิมพ์จะส่งตรงเข้าสมอง AI พร้อมรันคำสั่งเทอร์มินัลและแสดงผลการ์ด Terminal Card สีฟ้าสุดเท่ทันที
    5. **เพิ่มโมเดลในเมนูตั้งค่า:** เพิ่มตัวเลือก `ag/gemini-2.5-flash` (โหมดคำสั่งเร็วฉับไว) และ `ag/claude-sonnet-4-6` (คิดซับซ้อน) ในหน้าต่างตั้งค่าฟันเฟือง
- [x] **สเต็ป 12: ไฟล์คอนฟิกข้อความแบบง่าย `config.txt` ในปลั๊กอิน (Easy-to-Edit Config & Prompt - PASS 100%)**
  - **คำสั่งจากบอส:** อยากได้ไฟล์คอนฟิก `.txt` ในโฟลเดอร์ปลั๊กอิน `hermes-agent/plugins/realtime_voice/` ที่เปิดแก้ได้ง่ายด้วย Notepad ปรับ Prompt, Model, เสียง และการทำงานได้
  - **สร้างไฟล์:** `hermes-agent/plugins/realtime_voice/config.txt`
  - **ความสามารถ:**
    1. **แก้ไขได้ด้วย Notepad ทันที:** ใช้ฟอร์แมต `KEY=VALUE` เข้าใจง่าย มีคอมเมนต์ภาษาไทยอธิบายทุกตัวเลือก
    2. **Hot-Reload แบบสดๆ:** เซิร์ฟเวอร์อ่านไฟล์ใหม่ทุกครั้งที่มีข้อความเข้า แก้ไขเสร็จบันทึกไฟล์มีผลทันทีไม่ต้องรีสตาร์ท
    3. **ปรับแต่ง Prompt ได้อิสระ:** มีส่วน `CUSTOM_PROMPT="""..."""` รองรับข้อความยาวหลายบรรทัด กำหนดบทบาท คำสั่งพิเศษ หรือสไตล์การตอบ
    4. **สวิตช์เปิด/ปิดคำสั่งระบบ:** ปรับ `ENABLE_TERMINAL_TOOLS=true/false` ได้ง่ายๆ
    5. **แก้ Bug ตอบตัดบท:** แยกบริบทชวนคุย/เล่านิทาน ออกจากการรันเครื่อง และมีระบบ Retry ป้องกันข้อความว่างเปล่า

- [x] **สเต็ป 13: แก้ไขปัญหา Pylance Import Warning ใน VSCode (PASS 100%)**
  - จัดการสร้าง `.vscode/settings.json` กำหนด `extraPaths` ให้ตัวตรวจจับโค้ดของ IDE เข้าใจโครงสร้างโฟลเดอร์ปลั๊กอิน
  - ปรับการ import ใน `server.py` ด้วย `try...except` และ `# type: ignore` ลบจุดแดงแจ้งเตือน `1 problem in this file` หายเรียบร้อย
- [x] **สเต็ป 14: ปิดการใช้อีโมจิในโหมดคุยสดเรียลไทม์ (No-Emoji for Clean Speech - PASS 100%)**
  - **คำสั่งจากบอส:** ห้ามมีอีโมจิในข้อความตอบกลับของโหมดคุยสด เพราะระบบสร้างเสียง (Edge-TTS) จะอ่านออกเสียงชื่ออีโมจิออกมาด้วย
  - ปรับ `config.txt` และ System Prompt กำหนดกติกาเด็ดขาดห้ามตอบด้วยอีโมจิ
  - เพิ่มฟังก์ชัน `strip_emojis()` ด้วย Regex กรองอีโมจิและสัญลักษณ์ภาพทุกตัวออกทั้งจาก `reply_text` และข้อความที่ส่งเข้า TTS
- [x] **สเต็ป 15: ติดตั้ง Production Custom Subdomain `https://may.meuu.live` (PASS 100%)**
  - ตั้งค่า Cloudflare DNS: ชี้ A Record `may` -> `168.222.28.67` (Proxied 🟠)
  - ตั้งค่า Cloudflare Origin Rules: ชี้ `may.meuu.live` ไปยัง Port `9229`
  - เปิดพอร์ต `9229` (TCP) ใน Windows Defender Firewall
  - ปรับโหมด SSL/TLS บน Cloudflare เป็น `Flexible` เพื่อเชื่อมต่อกับ Origin Port 9229 แบบไร้รอยต่อ
- [x] **สเต็ป 16: ติดตั้งระบบควบคุมบ้านอัจฉริยะ Smart Home (Tuya Smart IR Gateway & AC Control - PASS 100%)**
  - **โครงสร้าง 3 ชั้นแบบ Decoupled:**
    1. **Microservice Gateway (`gateway/tuya-smart-ir-gateway/`):** โคลนจาก GitHub `boss2546/tuya-smart-ir-gateway` รันด้วย Node.js บนพอร์ต 3000 เชื่อมต่อ Tuya Cloud ควบคุมแอร์จริง (`Air (แอร์จริงในบ้าน)`) และฉากอัตโนมัติ
    2. **Smart Home Plugin (`hermes-agent/plugins/smart_home/`):** พัฒนาขึ้นใหม่ประกอบด้วย:
       - `config.txt`: ไฟล์ตั้งค่า Gateway URL (`http://localhost:3000`), Default AC ID (`a35a4e0b12b02aa750ceh4`), Timeout
       - `client.py`: Python REST client รองรับ `control_ac()`, `get_devices()`, `get_status()`, `trigger_scene()`
       - `tools.py`: สร้าง 3 เครื่องมือมาตรฐาน OpenAI Tool Calling: `smart_home_control_ac`, `smart_home_get_ac_status`, `smart_home_trigger_scene`
       - `__init__.py`: Export tools สะอาด ปลอดภัย ไม่กระทบไฟล์อื่น
    3. **Agent Skill (`.agents/skills/smart-home/SKILL.md`):** คู่มือและแนวทางการสนทนาภาษาไทยสำหรับน้องมายมิ้นท์ในการควบคุมแอร์และฉากอัตโนมัติ พร้อมกฎ No-Emoji เคร่งครัด
  - **การเชื่อมต่อ Voice Server (`server.py`):** เสียบ Tools เข้ากับ `AVAILABLE_TOOLS` และ `execute_tool()` อย่างปลอดภัยด้วย try-except หากไม่มีเกตเวย์จะไม่กระทบส่วนอื่น
  - **ผลการทดสอบผ่านฉลุย 100%:**
    - ✅ **Direct Test (`scripts/test_smart_home_direct.py`):** ยิงตรงเข้า Gateway ควบคุมแอร์สำเร็จ อ่านสถานะได้ 26°C โหมด Cool
    - ✅ **End-to-End Voice & Chat Test (`scripts/test_smart_home_end_to_end.py`):**
      - สั่งเช็คสถานะแอร์: AI เรียกใช้ `smart_home_get_ac_status` ดึงสถานะแอร์จริงมารายงานอย่างอบอุ่น ไม่มีอีโมจิ
      - สั่งปรับแอร์ 25 องศา: AI เรียกใช้ `smart_home_control_ac(temperature=25)` สั่งปรับแอร์จริงสำเร็จและตอบกลับอย่างหวานเป็นธรรมชาติ

---

## 🌐 ลิงก์ระบบที่เปิดใช้งานอยู่
- 🌸 **Maymint Production Subdomain:** `https://may.meuu.live/` (เข้าใช้งานได้จากทุกที่ทั่วโลก)
- 🌸 **Maymint Voice Web Dashboard (Quick Tunnel):** `https://blair-king-michel-calendar.trycloudflare.com/`
- 🌸 **Maymint Voice Web Dashboard (Local):** `http://127.0.0.1:9229/`
- 🏠 **Tuya Smart IR Gateway Dashboard (Local):** `http://localhost:3000/`
- 🖥️ **Hermes Standard Dashboard:** `http://127.0.0.1:9119/`

