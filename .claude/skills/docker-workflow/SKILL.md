---
name: docker-workflow
description: มาตรฐานการทำงานกับ Docker และ Docker Compose ฉบับสมบูรณ์แบบ 100% สำหรับสาย Vibe Coding และนักพัฒนา: สถาปัตยกรรม 3 ตู้ (หน้าบ้าน, หลังบ้าน, โกดัง), วงจรชีวิต Docker (Dockerfile -> Image -> Container -> Volume -> Port), คำสั่งควบคุมประจำวัน, การแก้โค้ดสด (Live Reload), ดูฐานข้อมูลผ่านเว็บ (Adminer), ภาษาไทย utf8mb4, Healthcheck และคู่มือแก้ปัญหา
---

# 🐳 Docker Workflow Skill (ฉบับสมบูรณ์แบบ 100% สำหรับสาย Vibe Coding & Developers)

คู่มือมาตรฐานระดับสากลสำหรับ AI ในการร่วมงานกับผู้ใช้เพื่อสร้าง ออกแบบ จัดการ และแก้ปัญหาการทำงานกับ **Docker & Docker Compose** ตั้งแต่วิธีคิดพื้นฐาน คำสั่งในชีวิตประจำวัน จนถึงการสร้างระบบเว็บแบบแยก 3 ตู้ที่ราบรื่นและเป็นมืออาชีพ

---

## 🎯 1. สถาปัตยกรรมหลัก: กฎ 3 ตู้ (ร้านอาหารโมเดล)

เมื่อผู้ใช้ต้องการสร้างหรือพัฒนาเว็บ ให้ยึดโครงสร้าง **แยก 3 ตู้เสมอ** (ห้ามยัดทุกอย่างรวมกันในตู้เดียวเด็ดขาด เพื่อความเป็นระเบียบ ไม่ตีกัน และขยายต่อยอดง่าย):

| ตู้ / Service | บทบาทในร้านอาหาร | หน้าที่ในระบบจริง | พอร์ตภายนอกแนะนำ | สิ่งที่เกิดขึ้นจริง |
| :--- | :--- | :--- | :--- | :--- |
| **🎨 1. Frontend** | **หน้าร้าน / เล่มเมนูอาหาร** | **คุยกับคน (ผู้ใช้):** แสดงผลหน้าจอ ปุ่มกด ฟอร์มกรอกข้อมูล รูปภาพ (HTML/CSS/JS, React, Vue, Vite, Next.js) | `3000` | ลูกค้าเปิดดูหน้าเว็บผ่านพอร์ตนี้บนเบราว์เซอร์ |
| **🧠 2. Backend API** | **ห้องครัว / พ่อครัวปรุงอาหาร** | **คิดคำนวณและตรรกะ:** รับคำสั่งจากหน้าบ้าน ตรวจสอบความถูกต้อง คิดคำนวณ แล้วสั่งบันทึกข้อมูล (Node.js, Express, Python FastAPI, Go) | `3001` | รับคำสั่ง HTTP Request และตอบกลับข้อมูล JSON |
| **🗄️ 3. Database** | **ตู้เย็นแช่ของ / โกดังวัตถุดิบ** | **เก็บของลงฮาร์ดดิสก์ถาวร:** บันทึกข้อมูลลงฐานข้อมูล ปิดเครื่องหรือปิดตู้ ข้อมูลก็ไม่สูญหาย (MySQL 8.4, PostgreSQL 16) | `3307` | มี Volume ผูกกับดิสก์เครื่องจริง (หลบพอร์ต 3306 ของเครื่อง) |
| **🖥️ 4. Adminer (เสริม)** | **หน้าต่างกระจกดูในโกดัง** | **จัดการฐานข้อมูลผ่านเบราว์เซอร์:** เปิดดู แก้ไข ตารางในฐานข้อมูลได้ทันทีผ่านเว็บ โดยไม่ต้องลงโปรแกรม DBeaver ในเครื่อง | `8085` | อำนวยความสะดวกให้ผู้ใช้สาย Vibe Coding |
| **⚡ 5. Redis (เสริม)** | **โต๊ะเสิร์ฟด่วน / ตู้แคชความเร็วสูง** | **พักข้อมูลชั่วคราว:** เก็บเซสชัน แคชข้อมูลที่เรียกซ้ำๆ เพิ่มความเร็วให้ระบบแบบติดจรวด | `6379` | แคชข้อมูลความเร็วสูงในแรม |

---

## 🧠 2. เสาหลักหัวใจของ Docker (Mental Model ฉบับเข้าใจง่ายที่สุดในโลก)

เพื่อให้ผู้ใช้สาย Vibe Coding เห็นภาพชัดเจน ให้ AI อธิบายกลไกของ Docker ด้วยภาพเปรียบเทียบ 6 องค์ประกอบนี้เสมอ:

```text
 1. 📄 Dockerfile      ➔ พิมพ์เขียวสั่งประกอบเครื่อง / สูตรอาหารบอกวิธีเตรียมวัตถุดิบ
      │ (สั่ง docker build)
      ▼
 2. 🧊 Image           ➔ ข้าวกล่องสำเร็จรูปแช่แข็ง (ยกไปเวฟที่เครื่องไหนบนโลก รสชาติเหมือนเดิม 100%)
      │ (สั่ง docker run หรือ docker compose up)
      ▼
 3. 📦 Container       ➔ จานอาหารพร้อมกิน / เครื่องคอมพิวเตอร์จำลองเสมือน (พังได้ ลบทิ้งได้ สร้างใหม่ใน 1 วินาที)
      │
      ├── 💾 Volume    ➔ ตู้เซฟเก็บของถาวร (ตู้พัง ข้อมูลในตู้เซฟไม่หาย) + ท่อแก้โค้ดสด (Live Reload)
      ├── 🚪 Port (-p) ➔ รูเจาะฝาตู้ให้คนภายนอกส่งของเข้าไปคุยกับข้างในได้ ("เลขพอร์ตเครื่องเรา:เลขพอร์ตในตู้")
      └── 🧶 Network   ➔ สายแลนเสมือนเชื่อมให้ตู้หน้าบ้าน หลังบ้าน โกดัง คุยกันผ่านชื่อตู้ได้ทันที
```

---

## 🔄 3. กลไกการไหลของข้อมูล และกฎเรื่อง CORS (Data Flow & CORS)

AI ต้องเข้าใจการทำงานประสานกันของทั้ง 3 ตู้ และ **ต้องปลดล็อก CORS ที่หลังบ้านเสมอ**:

```text
 👤 ผู้ใช้งาน (เปิดเว็บเบราว์เซอร์ http://localhost:3000)
      │
      ▼
 🎨 Frontend (หน้าบ้าน - พอร์ต 3000)
      │
      │ 1. ผู้ใช้กดปุ่ม ส่งคำสั่ง HTTP Request ข้ามพอร์ตไปหาพอร์ต 3001
      ▼ ⚠️ [ต้องเปิด CORS ที่หลังบ้าน ไม่งั้นเบราว์เซอร์จะบล็อกความปลอดภัยทันที!]
 🧠 Backend (หลังบ้าน - พอร์ต 3001 ภายนอก / พอร์ต 3000 ภายใน)
      │
      │ 2. ตรวจสอบความถูกต้อง คิดคำนวณ แล้วส่งคำสั่ง SQL ผ่านสายแลนในชื่อ 'db:3306'
      ▼
 🗄️ Database (ตู้ db - พอร์ต 3306 ภายในตู้ / 3307 ภายนอก)
      │
      │ 3. บันทึกข้อมูลลงฮาร์ดดิสก์ถาวร แล้วตอบกลับว่า "บันทึกสำเร็จ"
      ▼
 🧠 Backend (หลังบ้าน)
      │
      │ 4. ส่งผลลัพธ์ข้อมูลกลับไปแจ้งหน้าบ้านในรูปแบบ JSON
      ▼
 🎨 Frontend ➔ แสดงผลแจ้งเตือนสีเขียว "ทำรายการสำเร็จ!" ให้ผู้ใช้เห็นบนหน้าจอ
```

---

## 📁 4. โครงสร้างโฟลเดอร์มาตรฐาน (Standard 3-Tier Layout)

```text
my-project/
├── compose.yaml          # ผู้จัดการใหญ่ สั่งเปิด-ปิดทุกตู้พร้อมกัน และผูกสายแลนหากัน
├── .dockerignore         # รายการของต้องห้าม ไม่ให้หลุดเข้าไปหนักในตู้
├── frontend/             # โฟลเดอร์หน้าบ้าน
│   ├── Dockerfile
│   ├── index.html        # โค้ดหน้าจอ
│   └── (assets, js, css)
└── backend/              # โฟลเดอร์หลังบ้าน
    ├── Dockerfile
    ├── package.json      # คำสั่ง start ใช้ "node --watch app.js" เพื่อแก้โค้ดสดได้
    └── app.js            # โค้ดหลังบ้าน (Express + CORS + MySQL)
```

---

## 📋 5. แม่แบบไฟล์มาตรฐาน (The Golden Templates)

### 📄 5.1 แม่แบบ `compose.yaml` (ชุดสมบูรณ์ 4 ตู้ พร้อมระบบกันบั๊กสำคัญ)

```yaml
services:
  # 🎨 1. หน้าบ้าน (Frontend)
  frontend:
    build: ./frontend
    container_name: app_frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app         # 🔄 Live Reload: แก้โค้ดหน้าบ้านในเครื่อง เปลี่ยนทันทีในตู้
      - /app/node_modules       # 🛡️ Anonymous Volume: กันไฟล์เครื่องทับไฟล์ในตู้
    depends_on:
      - backend

  # 🧠 2. หลังบ้าน (Backend API)
  backend:
    build: ./backend
    container_name: app_backend
    restart: unless-stopped
    ports:
      - "3001:3000"
    depends_on:
      db:
        condition: service_healthy # ⏱️ วอร์มเครื่อง: รอให้ฐานข้อมูลพร้อม 100% ก่อน เว็บถึงค่อยเปิดตาม
    environment:
      DB_HOST: db
      DB_PORT: 3306
      DB_NAME: mydb
      DB_USER: root
      DB_PASSWORD: secret123
    volumes:
      - ./backend:/app          # 🔄 Live Reload: แก้โค้ดหลังบ้านในเครื่อง เซิร์ฟเวอร์รีสตาร์ทเองทันที
      - /app/node_modules       # 🛡️ Anonymous Volume: ป้องกันโฟลเดอร์ในเครื่องทับในตู้

  # 🗄️ 3. โกดังเก็บของ (Database MySQL 8.4)
  db:
    image: mysql:8.4
    container_name: app_db
    restart: unless-stopped
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci # 🇹🇭 ภาษาไทยไม่เป็น ???
    environment:
      MYSQL_ROOT_PASSWORD: secret123
      MYSQL_DATABASE: mydb
    ports:
      - "3307:3306"             # 🚪 หลบพอร์ต 3306 ของเครื่อง Mac
    volumes:
      - db_data:/var/lib/mysql  # 💾 ข้อมูลเก็บถาวรในตู้เซฟ ปิดตู้ข้อมูลไม่หาย
    healthcheck:                # 🩺 ตรวจสุขภาพฐานข้อมูล
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-psecret123"]
      interval: 5s
      timeout: 5s
      retries: 10

  # 🖥️ 4. หน้าต่างดูฐานข้อมูลผ่านเว็บ (Adminer)
  adminer:
    image: adminer:latest
    container_name: app_adminer
    restart: unless-stopped
    ports:
      - "8085:8080"
    depends_on:
      - db

volumes:
  db_data:                      # ตู้เซฟเก็บข้อมูลถาวร
```

---

### 📄 5.2 แม่แบบ `compose.postgres.yaml` (ทางเลือก PostgreSQL 16)

หากโปรเจกต์ต้องการใช้ PostgreSQL แทน MySQL:

```yaml
services:
  backend:
    build: ./backend
    container_name: app_backend
    restart: unless-stopped
    ports:
      - "3001:3000"
    depends_on:
      db:
        condition: service_healthy
    environment:
      DB_HOST: db
      DB_PORT: 5432
      DB_NAME: mydb
      DB_USER: postgres
      DB_PASSWORD: secret123
    volumes:
      - ./backend:/app
      - /app/node_modules

  db:
    image: postgres:16-alpine
    container_name: app_db
    restart: unless-stopped
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secret123
    ports:
      - "5433:5432"             # หลบพอร์ต 5432 ของเครื่อง
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 10

  adminer:
    image: adminer:latest
    container_name: app_adminer
    restart: unless-stopped
    ports:
      - "8085:8080"
    depends_on:
      - db

volumes:
  pg_data:
```

---

### 📄 5.3 แม่แบบ `backend/Dockerfile` (Node.js Alpine)

```dockerfile
FROM node:20-alpine

WORKDIR /app

# คัดลอก package.json มาติดตั้ง library ก่อน เพื่อใช้ประโยชน์จาก Docker Cache
COPY package*.json ./
RUN npm install

# คัดลอกโค้ดทั้งหมดเข้ามา
COPY . .

EXPOSE 3000

# ใช้ node --watch ใน package.json สตาร์ท เพื่อให้ Live Reload ทำงานอัตโนมัติ
CMD ["npm", "start"]
```

---

### 📄 5.4 แม่แบบ `backend/package.json` (เปิดโหมด Live Reload ด้วย `node --watch`)

```json
{
  "name": "backend",
  "version": "1.0.0",
  "scripts": {
    "start": "node --watch app.js"
  },
  "dependencies": {
    "express": "^4.19.2",
    "cors": "^2.8.5",
    "mysql2": "^3.9.7"
  }
}
```

---

### 📄 5.5 แม่แบบ `backend/app.js` (Express + CORS + MySQL Health Endpoint)

```javascript
const express = require('express');
const cors = require('cors');
const mysql = require('mysql2/promise');

const app = express();
app.use(cors()); // 🔓 ปลดล็อก CORS เสมอ เพื่อให้หน้าบ้านข้ามพอร์ตมาคุยได้
app.use(express.json());

// สร้าง Connection Pool ไปยังตู้ db
const pool = mysql.createPool({
  host: process.env.DB_HOST || 'db',
  port: parseInt(process.env.DB_PORT || '3306'),
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || 'secret123',
  database: process.env.DB_NAME || 'mydb',
  waitForConnections: true,
  connectionLimit: 10
});

// ตรวจสอบสุขภาพระบบ
app.get('/api/health', async (req, res) => {
  try {
    const [rows] = await pool.query('SELECT 1 + 1 AS result');
    res.json({ status: 'ok', message: 'Backend และ Database ทำงานสมบูรณ์ 100%', dbCheck: rows[0].result });
  } catch (err) {
    res.status(500).json({ status: 'error', message: err.message });
  }
});

const PORT = 3000;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Backend API พร้อมทำงานที่พอร์ต ${PORT}`);
});
```

---

### 📄 5.6 แม่แบบ `.dockerignore` (ป้องกันขยะและไฟล์สำคัญรั่วไหล)

```text
node_modules
npm-debug.log
.DS_Store
.vscode
.idea
.git
.gitignore
.env
```

---

## 🛠️ 6. คลังคำสั่งควบคุม Docker ในชีวิตประจำวัน (Daily Docker Operations Cheat Sheet)

AI ต้องเข้าใจและแนะนำคำสั่งเหล่านี้ให้ผู้ใช้ได้อย่างถูกต้อง พร้อมคำอธิบายคำต่อคำ:

### 🚀 6.1 คำสั่งเปิดและปิดระบบ (Compose Lifecycle)
* **เปิดทุกตู้ทำงานเบื้องหลัง:**
  ```bash
  docker compose up -d
  ```
  *(อธิบายผู้ใช้: `-d` คือ detached mode สั่งให้ทุกตู้แอบทำงานในพื้นหลัง ไม่บล็อกหน้าต่าง Terminal)*
* **เปิดพร้อมสั่งประกอบร่างใหม่ (เมื่อมีการแก้ Dockerfile หรือเพิ่ม library ใน package.json):**
  ```bash
  docker compose up -d --build
  ```
  *(อธิบายผู้ใช้: `--build` บังคับให้สร้างข้าวกล่อง Image ใหม่ เพื่อเอาของใหม่เข้าไปในตู้)*
* **ปิดระบบและเก็บกวาดตู้ทั้งหมดอย่างปลอดภัย (ข้อมูลใน Database ไม่หาย):**
  ```bash
  docker compose down
  ```
  *(อธิบายผู้ใช้: ปิดตู้และถอดสายแลนอย่างนุ่มนวล โดยตู้เซฟ Volume ยังอยู่ครบ 100%)*
* **⚠️ คำสั่งลบระบบพร้อมตู้เซฟทิ้ง (ระวัง! ข้อมูลใน Database จะหายเกลี้ยง):**
  ```bash
  docker compose down -v
  ```
  *(ใช้เฉพาะตอนต้องการล้างระบบเริ่มต้นใหม่จากศูนย์จริงๆ เท่านั้น)*

---

### 🔍 6.2 คำสั่งสืบสวนและตรวจเช็คสุขภาพ (Diagnostics)
* **ดูสถานะว่ามีตู้ไหนกำลังทำงานอยู่บ้าง:**
  ```bash
  docker compose ps
  ```
* **ดูสิ่งที่เกิดขึ้นข้างในตู้แบบสดๆ (Live Logs):**
  ```bash
  docker compose logs -f [service_name]
  # เช่น ดูหลังบ้าน:
  docker compose logs -f backend
  ```
  *(อธิบายผู้ใช้: `-f` คือ follow ติดตามดูข้อความ Error หรือ Log ล่าสุดแบบเรียลไทม์ กด Ctrl + C เพื่อออก)*
* **ดูข้อความย้อนหลัง 100 บรรทัดล่าสุด:**
  ```bash
  docker compose logs --tail=100 backend
  ```
* **ดูการกินทรัพยากร CPU และ RAM ของแต่ละตู้แบบเรียลไทม์:**
  ```bash
  docker stats
  ```

---

### ⚡ 6.3 คำสั่งปฏิบัติการภายในตู้ (โดยไม่ต้องปิดตู้)
* **ติดตั้ง Library ใหม่เข้าไปในตู้ทันที:**
  ```bash
  docker compose exec backend npm install [ชื่อแพ็กเกจ]
  # เช่น: docker compose exec backend npm install axios
  ```
* **มุดเข้าไปในตู้เพื่อสั่งคำสั่ง Terminal ภายใน:**
  ```bash
  docker compose exec backend sh
  ```
  *(พิมพ์ `exit` เพื่อออกจากตู้กลับมาที่เครื่อง Mac)*
* **สั่ง Migrate ฐานข้อมูล (เช่น Prisma):**
  ```bash
  docker compose exec backend npx prisma migrate dev
  ```
* **สั่งรีสตาร์ทเฉพาะตู้ที่มีปัญหา:**
  ```bash
  docker compose restart [service_name]
  # เช่น: docker compose restart backend
  ```

---

### 🧹 6.4 คำสั่งล้างขยะ Docker ทวงคืนพื้นที่ดิสก์ Mac อย่างปลอดภัย
```bash
docker system prune -a --volumes=false
```
*(อธิบายผู้ใช้: คำสั่งนี้จะลบเฉพาะ Image และ Container ขยะที่ตกค้าง โดยตั้งใจใส่ `--volumes=false` เพื่อปกป้องข้อมูลใน Database ไม่ให้หายเด็ดขาด 100%)*

---

## ⚠️ 7. กฎเหล็กในการทำงานของ AI กับผู้ใช้สาย Vibe Coding

1. **ไปทีละสเต็ป (Step-by-Step):**
   * ห้ามสร้างโค้ดยาวเหยียด 10 ไฟล์ในครั้งเดียว ให้แนะนำทีละขั้น ตรวจสอบทีละไฟล์
2. **ภาษาเข้าใจง่าย (Kindergarten Mental Model):**
   * อธิบายด้วยภาพเปรียบเทียบ (ร้านอาหาร, ตู้เซฟ, ข้าวกล่องแช่แข็ง) ไม่พ่นศัพท์เทคนิคล้วน
3. **อธิบายคำสั่ง Terminal คำต่อคำ:**
   * เช่น บอกว่า `-d` คือแอบรันเบื้องหลัง, `-p` คือเจาะรูเปิดพอร์ต, `-v` คือผูกตู้เซฟโฟลเดอร์
4. **ป้องกันข้อผิดพลาดล่วงหน้า:**
   * เตือนให้ผู้ใช้กด Save (`Cmd + S`) เสมอ
   * **เปิด CORS ที่ Backend เสมอ** เพื่อไม่ให้หน้าบ้านดึงข้อมูลแล้วโดนบล็อก
   * **หลบพอร์ตเครื่องจริงเสมอ** เช่น MySQL ใช้ `3307:3306`

---

## 🔍 8. คู่มือแก้ปัญหาด่วน 9 อาการยอดฮิต (Troubleshooting Playbook)

| อาการ / ข้อความ Error | สาเหตุที่แท้จริง | วิธีแก้ปัญหาทันที |
| :--- | :--- | :--- |
| **1. พอร์ตชน (`bind: address already in use` หรือ `already allocated`)** | มีโปรแกรมอื่นในเครื่อง Mac กำลังใช้พอร์ตนั้นอยู่ (เช่น รัน MySQL ไว้นอก Docker) | เปลี่ยนเลขพอร์ตตัวหน้าใน `compose.yaml` (เช่น เปลี่ยน `"3001:3000"` เป็น `"3002:3000"`) แล้วรัน `docker compose up -d` ใหม่ |
| **2. ตู้ดับทันที (`Exited with code 0 หรือ 1`)** | โค้ดในโปรแกรมมี Syntax Error หรือคำสั่ง start สั่งผิด | รัน `docker compose logs [ชื่อตู้]` เพื่ออ่านบรรทัดที่พัง แล้วแก้โค้ดที่ไฟล์นั้น |
| **3. ตู้ดับจากแรมหมด (`Exit code 137`)** | Container ถูกระบบตัดการทำงานเพราะแรมไม่พอ (OOM) | ปรับเพิ่มแรมใน Docker Desktop Settings หรือตรวจดูการกินแรมด้วย `docker stats` |
| **4. หน้าบ้านเรียกหลังบ้านแล้วบล็อก (CORS Error: `No Access-Control-Allow-Origin`)** | เบราว์เซอร์บล็อกการส่งข้อมูลข้ามพอร์ต | ใน Backend ให้ลงแพ็กเกจ `npm install cors` แล้วใส่ `app.use(cors())` ด้านบนสุดของ Express |
| **5. หลังบ้านต่อ MySQL ไม่ได้ (`ECONNREFUSED`)** | หลังบ้านตื่นก่อน ฐานข้อมูลยังวอร์มเครื่องไม่เสร็จ (Cold-Start) | ใส่ `healthcheck` ในตู้ db, ใส่ `depends_on: db: condition: service_healthy` และเขียน Retry Loop ในโค้ดหลังบ้านอย่างน้อย 10-15 รอบ (หน่วงเวลารวม 20-30 วินาที) |
| **6. ข้อมูลภาษาไทยใน MySQL กลายเป็น `???`** | Charset ของ MySQL เป็น `latin1` เริ่มต้น | ใส่ `command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci` ในตู้ db |
| **7. แก้โค้ดในเครื่องแล้ว หน้าเว็บไม่เปลี่ยน (Live Reload ไม่ทำงาน)** | ไม่ได้ผูก Volume หรือไม่มีคำสั่ง watch ใน container | ตรวจสอบว่าใน `compose.yaml` มี `volumes: - ./backend:/app` และใน `package.json` รันด้วย `node --watch app.js` |
| **8. DBeaver ต่อ MySQL 8 ไม่ได้ (`Public Key Retrieval is not allowed`)** | ระบบความปลอดภัยรหัสผ่านแบบใหม่ของ MySQL 8 | ใน DBeaver ไปที่ Driver properties แล้วเปลี่ยน `allowPublicKeyRetrieval` เป็น `true` หรือเปิด Adminer ที่ `http://localhost:8085` แทน |
| **9. YAML พัง (`mapping values are not allowed` หรือ `could not find ':'`)** | การเคาะเว้นวรรค (Indentation) ผิด หรือลืมเว้นวรรคหลังเครื่องหมาย `:` | ใน YAML ต้องใช้ Spacebar เสมอ ห้ามใช้ Tab และหลัง `:` ต้องเคาะเว้นวรรค 1 ครั้งเสมอ |
| **10. Worker / บอททำงานเบื้องหลังแอบดับเงียบ (`Connection closed` หรือ `OperationalError`)** | ถือท่อ Connection ฐานข้อมูลค้างข้ามลูป หรือเจอ MySQL Idle Timeout | ใช้รูปแบบ **Acquire-Use-Release (เบิก-ใช้-คืน)** ต่อรอบลูป ห้ามถือท่อค้างข้ามลูป และเปิดระบบตรวจความสดใหม่ของท่อ (`pool_pre_ping=True`) |

---

## 🪜 9. ขั้นตอนการย้ายโปรเจกต์เดิมเข้า Docker ทีละก้าว (Step-by-Step Migration Guide)

หากผู้ใช้มีโปรเจกต์เดิมที่รันบนเครื่อง Mac อยู่แล้ว และต้องการย้ายเข้า Docker 3 ตู้ ให้ AI ดำเนินการตาม 5 สเต็ปนี้:

1. **สเต็ปที่ 1: จัดโฟลเดอร์แยก 2 ฝั่ง**
   * สร้างโฟลเดอร์ `frontend/` และย้ายโค้ดหน้าบ้าน (HTML, CSS, JS, React) เข้าไป
   * สร้างโฟลเดอร์ `backend/` และย้ายโค้ดหลังบ้าน (API, server.js) เข้าไป
2. **สเต็ปที่ 2: สร้างไฟล์ `.dockerignore` ที่โฟลเดอร์หลัก**
   * ใส่ `node_modules`, `.git`, `.env` เพื่อกันไม่ให้ไฟล์ขยะหลุดเข้าตู้
3. **สเต็ปที่ 3: สร้าง `Dockerfile` ให้แต่ละตู้**
   * สร้าง `frontend/Dockerfile` และ `backend/Dockerfile`
4. **สเต็ปที่ 4: สร้าง `compose.yaml`**
   * กำหนด services: `frontend`, `backend`, `db` (MySQL 8.4) และ `adminer`
   * ผูก Volume แก้โค้ดสด และตั้งค่า Healthcheck
5. **สเต็ปที่ 5: สั่งรันและตรวจสอบ**
   * รัน `docker compose up -d --build`
   * ตรวจสอบด้วย `docker compose ps` และเปิดทดสอบที่เบราว์เซอร์ `http://localhost:3000`

---

## 💬 10. คลังคำสั่งสำเร็จรูปสำหรับผู้ใช้ (The Ultimate Magic Prompts)

ผู้ใช้สามารถก๊อปปี้ข้อความเหล่านี้ไปสั่ง AI ได้ทันที:

### 🌟 กลุ่มที่ 1: การเริ่มและปรับโครงสร้าง
* **1.1 ปรับโครงสร้างโปรเจกต์เดิมให้รองรับ Docker 3 ตู้ (Migration):**
  > "ช่วยปรับโครงสร้างโค้ดและไฟล์ทั้งหมดในโปรเจกต์นี้ ให้รองรับ Docker ตามมาตรฐาน 3 ตู้ (docker-workflow) ให้หน่อย: สำรวจไฟล์ปัจจุบัน จัดลง frontend/ และ backend/, ทำ Dockerfile แต่ละตู้, สร้าง .dockerignore และ compose.yaml พร้อม Volume แก้โค้ดสด รองรับภาษาไทยและ CORS ทำทีละสเต็ปนะ"
* **1.2 เริ่มโปรเจกต์ใหม่ตั้งแต่ศูนย์ (Scaffolding):**
  > "ฉันจะเริ่มทำโปรเจกต์ใหม่ ช่วยวางโครงสร้างระบบแบบ 3 ตู้ด้วย Docker Compose (docker-workflow) ให้หน่อย: Frontend พอร์ต 3000, Backend พอร์ต 3001, Database MySQL 8.4 พอร์ต 3307 พร้อมตั้งค่า UTF-8 ภาษาไทยและ CORS ให้เสร็จสรรพ"

### 🛠️ กลุ่มที่ 2: การต่อเติมฟังก์ชัน
* **2.1 เพิ่มตู้หน้าเว็บดูฐานข้อมูล (Adminer) ไม่ต้องลง DBeaver ในเครื่อง:**
  > "ช่วยเพิ่มตู้ดูฐานข้อมูลผ่านเบราว์เซอร์ (Adminer) ลงใน compose.yaml ตามสกิล docker-workflow ให้หน่อย ขอพอร์ต 8085 เพื่อให้ฉันเปิดดูตารางในเบราว์เซอร์ได้เลยโดยไม่ต้องลงโปรแกรมในเครื่อง"
* **2.2 เพิ่มตู้แคชความเร็วสูง (Redis):**
  > "ช่วยเพิ่มตู้ Redis ลงใน compose.yaml ให้หน่อย พร้อมตั้งชื่อตู้และผูก Network เข้ากับ Backend ตามมาตรฐานสกิล docker-workflow"
* **2.3 สลับชนิดฐานข้อมูล (เช่น จาก MySQL เป็น PostgreSQL หรือ MongoDB):**
  > "ฉันต้องการเปลี่ยนฐานข้อมูลจาก MySQL ไปเป็น PostgreSQL ช่วยปรับแก้ compose.yaml และคอนฟิกใน Backend ให้ถูกต้องตามมาตรฐาน โดยย้าย Volume ข้อมูลให้อย่างปลอดภัย"

### 📦 กลุ่มที่ 3: การดูแลรักษาและจัดการภายในตู้
* **3.1 ติดตั้ง Library ใหม่เข้าไปในตู้โดยไม่ต้อง Build ใหม่:**
  > "ฉันต้องการติดตั้ง library [ชื่อแพ็กเกจ เช่น express หรือ cors] เพิ่มใน Backend ช่วยบอกคำสั่งรันผ่าน docker compose exec หรือจัดการอัปเดตไฟล์ให้ถูกต้องทีละสเต็ปหน่อย"
* **3.2 ล้างขยะ Docker คืนพื้นที่ฮาร์ดดิสก์ Mac อย่างปลอดภัย:**
  > "ช่วยบอกคำสั่งและวิธีล้าง Image/Container เก่าๆ ที่ไม่ได้ใช้งานใน Docker เพื่อคืนพื้นที่ฮาร์ดดิสก์ให้ Mac หน่อย ขอวิธีที่ปลอดภัยไม่ลบข้อมูลในฐานข้อมูลนะ"

### 🚨 กลุ่มที่ 4: การสืบสวนและแก้ปัญหา
* **4.1 สวมบทนักสืบแก้บั๊ก:**
  > "ฉันรัน Docker แล้วเจอ Error นี้: [แปะข้อความ Error] ช่วยสวมบทนักสืบตามสกิล docker-workflow อธิบายให้เข้าใจง่ายๆ แบบเด็กอนุบาลว่าพังเพราะอะไร และบอกวิธีแก้ทีละบรรทัดให้ด้วย"
* **4.2 เช็คสุขภาพและตรวจดูการกินทรัพยากร:**
  > "ช่วยเขียนคำสั่งตรวจสอบว่าตอนนี้ตู้ไหนกำลังกิน CPU/RAM เท่าไหร่ และตรวจเช็คว่าทุกตู้ยังทำงานปกติดีอยู่ไหม"

### 🤝 กลุ่มที่ 5: การเตรียมส่งต่องาน
* **5.1 ตรวจความพร้อมก่อนส่งต่อให้เพื่อนร่วมทีม:**
  > "ช่วยตรวจเช็คไฟล์ .dockerignore และ compose.yaml ของโปรเจกต์นี้ให้พร้อมส่งต่อให้เพื่อนร่วมทีมหน่อย และช่วยเขียนสรุปคำสั่ง 1 บรรทัดที่เพื่อนต้องรันให้ด้วย"

### 🏭 กลุ่มที่ 6: การยกระดับสู่ Production (Upgrade to Production)
* **6.1 ส่งไม้ต่อไปยังสกิล `production-architecture`:**
  > "ฉันพัฒนาโปรเจกต์ด้วย docker-workflow ในเครื่องเสร็จสมบูรณ์แล้ว ตอนนี้พร้อมนำขึ้นเซิร์ฟเวอร์จริง ช่วยยกระดับระบบนี้ไปใช้มาตรฐาน production-architecture ให้หน่อย: ใส่ NGINX Gateway ด่านหน้า, ปิดพอร์ต 3000/3001 ภายใน, ตั้ง Log Rotation กันดิสก์เต็ม, เปิด Auto-Restart, และแนะนำการตั้งไฟร์วอลล์ UFW กับ Cloudflare ทีละสเต็ปนะ"

---

## 🔗 11. สะพานเชื่อมสู่ Production (The Bridge to `production-architecture`)

เมื่อคุณและ AI ร่วมกันพัฒนาโค้ด ฟังก์ชัน และหน้าเว็บในเครื่องของคุณ (Localhost) จนเสร็จสมบูรณ์ 100% ตามมาตรฐาน `docker-workflow` แล้ว และถึงเวลาที่จะนำระบบขึ้นเซิร์ฟเวอร์จริง (VPS / Cloud Server เช่น Ubuntu บน DigitalOcean, Linode, AWS หรือผูกกับโดเมน เช่น `meuu.live`):

**ระบบจะส่งไม้ต่อไปยังสกิล `production-architecture` ทันที!** โค้ด หน้าบ้าน หลังบ้าน และฐานข้อมูลเดิมของคุณจะถูกนำมาสวมเกราะป้องกันระดับองค์กรโดยไม่ต้องเขียนระบบใหม่ตั้งแต่ต้น

### 📊 ตารางเปรียบเทียบการเปลี่ยนผ่าน (Dev vs Production Transition)

| มิติการทำงาน | โหมดพัฒนาในเครื่อง (`docker-workflow`) | โหมดใช้งานจริงบนเซิร์ฟเวอร์ (`production-architecture`) |
| :--- | :--- | :--- |
| **ด่านหน้ารับผู้ใช้** | เปิดพอร์ตตรงๆ (Frontend `3000`, Backend `3001`) | มี **NGINX Gateway (`80`/`443`)** รับแขกหน้าสุด |
| **การเข้าถึง Backend** | ยิงตรง `http://localhost:3001/api` (ต้องเปิด CORS) | วิ่งผ่าน NGINX ที่ path `/api/` (ไม่ต้องกังวลเรื่อง CORS อีกต่อไป) |
| **การเข้าถึง Database** | เปิดพอร์ต `3307` ให้ Adminer/DBeaver ต่อได้ | ปิดพอร์ตภายนอกมิดชิด ผูกเฉพาะ `127.0.0.1` ภายในโฮสต์ |
| **Adminer Web GUI** | เปิดพอร์ต `8085` เพื่อความสะดวกในการดูตาราง | **ปิดทิ้ง (Disable)** ป้องกันบุคคลภายนอกเข้าถึงฐานข้อมูล |
| **การโหลดโค้ด** | ผูก Volume (`./frontend:/app`) เพื่อ Live Reload สดๆ | **Build เป็น Image ถาวร** เพื่อความเร็ว เสถียรภาพ และไม่มีการแก้สดบนโปรดักชัน |
| **การจัดการ Log** | แสดงออกทางคอนโซลปกติ | มี **Log Rotation (`10m`, 3 files)** ป้องกันฮาร์ดดิสก์เซิร์ฟเวอร์เต็ม |
| **การฟื้นตัว (Restart)** | ปิดเปิดเองตามสั่ง | **`restart: unless-stopped`** เซิร์ฟเวอร์รีบูต ตู้ฟื้นเองอัตโนมัติ |
| **การรักษาความปลอดภัย** | รันบน localhost ไม่มีไฟร์วอลล์ | **Host Firewall (UFW)** + **Cloudflare Proxied 🟠** ซ่อน IP จริง |
| **การสำรองข้อมูล** | บันทึกเฉพาะในดิสก์เครื่อง | มีตู้ **Auto DB Backup** แอบดัมป์ SQL ทุกเที่ยงคืน ย้อนหลัง 7 วัน |

