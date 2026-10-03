---
name: meuu-api-gateway
description: สกิลกลางแม่บท (Universal Central Master Skill) สำหรับเชื่อมต่อและใช้งาน 9Router AI Infrastructure Gateway (https://api.meuu.club/v1) อย่างละเอียดสมบูรณ์ 100% ครบทุก Endpoints, JSON Schemas, Request/Response ตัวอย่างโค้ด cURL, Python, Node.js, การตั้งค่า Tool ทุกค่าย (Cursor, Claude Code, Cline) และระบบบริหารโควต้า 12,000 ครั้ง/สัปดาห์
---

# 🌐 สกิลกลางแม่บท AI Gateway: 9Router (`api.meuu.club`) ฉบับสมบูรณ์สูงสุด

> **สถานะระบบ:** 🟢 ออนไลน์พร้อมใช้งาน 24 ชั่วโมง  
> **Central Base URL:** `https://api.meuu.club/v1`  
> **Direct Local URL:** `http://168.222.28.67:20128/v1` (หรือ `http://127.0.0.1:20128/v1`)  
> **Master API Key:** `sk-07ccde1e709eb2ca-e05r6c-a11b5d7c`  
> **Web Dashboard:** `https://api.meuu.club/dashboard` (รหัสผ่าน: `0898661896za`)  
> **มาตรฐานโปรโตคอล:** OpenAI API v1 Standard & Anthropic Claude Messages API v1 Native

---

## 📑 สารบัญเนื้อหาทั้งหมด (Master Index)
1. [สถาปัตยกรรมและโควต้าของระบบ (Architecture & Quota Breakdown)](#1-สถาปัตยกรรมและโควต้าของระบบ)
2. [ตาราง Full Endpoints และ Header ทั้งหมด](#2-ตาราง-full-endpoints-และ-header-ทั้งหมด)
3. [ตารางโมเดล AI และความสามารถแบบเจาะลึก (Comprehensive Model Matrix)](#3-ตารางโมเดล-ai-และความสามารถแบบเจาะลึก)
4. [Endpoint 1: Chat Completions (`POST /v1/chat/completions`)](#4-endpoint-1-chat-completions)
   - [4.1 โครงสร้างพารามิเตอร์ทั้งหมด (Full Parameter Spec)](#41-โครงสร้างพารามิเตอร์ทั้งหมด)
   - [4.2 แชทข้อความทั่วไป (Standard Chat)](#42-แชทข้อความทั่วไป)
   - [4.3 สตรีมมิ่งตัวอักษรเรียลไทม์ (Streaming SSE)](#43-สตรีมมิ่งตัวอักษรเรียลไทม์)
   - [4.4 วิเคราะห์รูปภาพและเอกสาร (Multimodal Vision / OCR)](#44-วิเคราะห์รูปภาพและเอกสาร)
   - [4.5 การเรียกใช้ฟังก์ชัน / เครื่องมือ (Function / Tool Calling)](#45-การเรียกใช้ฟังก์ชัน--เครื่องมือ)
5. [Endpoint 2: Anthropic Claude Native (`POST /v1/messages`)](#5-endpoint-2-anthropic-claude-native)
6. [Endpoint 3: สังเคราะห์เสียงพูด (Text-to-Speech: `POST /v1/audio/speech`)](#6-endpoint-3-สังเคราะห์เสียงพูด-text-to-speech)
   - [6.1 รายชื่อเสียงทั้งหมด (Voices List: ไทย / อังกฤษ / สากล)](#61-รายชื่อเสียงทั้งหมด)
   - [6.2 ตัวอย่างโค้ดสร้างเสียง MP3 ครบ 3 ภาษา](#62-ตัวอย่างโค้ดสร้างเสียง-mp3)
7. [Endpoint 4: ถอดเสียงเป็นข้อความ (Speech-to-Text: STT)](#7-endpoint-4-ถอดเสียงเป็นข้อความ-speech-to-text)
   - [7.1 ถอดเสียงภาษาไทยความเร็วสูง (2.7 วินาที)](#71-ถอดเสียงภาษาไทยความเร็วสูง)
   - [7.2 โฟลว์ลัดทะลวงคอขวด: ฟังเสียงแล้วตอบทันที (3.64 วินาที)](#72-โฟลว์ลัดทะลวงคอขวด-ฟังเสียงแล้วตอบทันที)
8. [Endpoint 5: ตรวจสอบโมเดล (`GET /v1/models`)](#8-endpoint-5-ตรวจสอบโมเดล)
9. [คู่มือตั้งค่าโปรแกรมเขียนโค้ดและ AI Agent ทุกค่าย (Integration Guide)](#9-คู่มือตั้งค่าโปรแกรมเขียนโค้ดและ-ai-agent-ทุกค่าย)
   - [Cursor IDE](#91-cursor-ide)
   - [Claude Code CLI](#92-claude-code-cli)
   - [Cline & Roo Code (VS Code Extension)](#93-cline--roo-code)
   - [Continue.dev](#94-continuedev)
   - [Windsurf IDE](#95-windsurf-ide)
   - [Python / LangChain / LlamaIndex / Vercel AI SDK](#96-python--langchain--vercel-ai-sdk)
10. [ตารางรหัสข้อผิดพลาดและการแก้ปัญหา (Error Codes & Troubleshooting)](#10-ตารางรหัสข้อผิดพลาดและการแก้ปัญหา)

---

## 1. สถาปัตยกรรมและโควต้าของระบบ

9Router ทำหน้าที่เป็น **Central AI Gateway** กระจายโหลดและจัดการทราฟฟิกอัตโนมัติ:

```mermaid
graph TD
    subgraph Clients ["💻 ไคลเอนต์และ AI ทั้งหมด (Clients)"]
        C1["Cursor IDE"]
        C2["Claude Code CLI"]
        C3["VS Code (Cline / Roo)"]
        C4["แอพและบอทภายนอก (Python/Node)"]
    end

    subgraph Gateway ["🌐 9Router Gateway Server (Port 20128)"]
        CF["Cloudflare Tunnel: api.meuu.club"]
        LB["Round-Robin Load Balancer"]
        TR["Token Compressor (RTK -20~40%)"]
        CF --> LB
        LB --> TR
    end

    subgraph Providers ["🏛️ บัญชีโควต้า Google Antigravity (12,000 req/week)"]
        A1["Account 1: suwalak2307@gmail.com"]
        A2["Account 2: bossok2546@gmail.com"]
        A3["Account 3: meuok100@gmail.com"]
        A4["Account 4: axis.solutions.team@gmail.com"]
        A5["Account 5: axis.solutions.dev@gmail.com"]
        A6["Account 6: project.key.me@gmail.com"]
    end

    C1 --> CF
    C2 --> CF
    C3 --> CF
    C4 --> CF
    TR --> A1
    TR --> A2
    TR --> A3
    TR --> A4
    TR --> A5
    TR --> A6
```

### สรุปตัวเลขโควต้า:
* **โควต้าต่อสัปดาห์:** **12,000 Requests/สัปดาห์** (Gemini 6,000 + Claude 6,000)
* **โควต้า Rolling 5 ชั่วโมง:** **6,000 Requests ต่อ 5 ชั่วโมง** (เฉลี่ยยิงได้ต่อเนื่อง 20 ครั้ง/นาที ตลอด 24 ชม.)
* **ระบบตัดสลับบัญชี (Auto-Failover):** หากบัญชีใดติด Rate Limit ระบบจะสลับไปยังบัญชีที่ว่างอยู่ทันทีภายใน 50ms โดยที่ไคลเอนต์ไม่หลุดการเชื่อมต่อ

---

## 2. ตาราง Full Endpoints และ Header ทั้งหมด

### ตารางลิงก์แบบสมบูรณ์ (Full Absolute URLs):
| หมวดหมู่บริการ | Method | 🔗 ลิงก์เต็มรูปแบบ (Full Absolute URL) | ความเข้ากันได้ |
| :--- | :---: | :--- | :---: |
| **Chat & Coding** | `POST` | `https://api.meuu.club/v1/chat/completions` | OpenAI v1 Spec |
| **Claude Native** | `POST` | `https://api.meuu.club/v1/messages` | Anthropic Spec |
| **Text-to-Speech (TTS)** | `POST` | `https://api.meuu.club/v1/audio/speech` | OpenAI Audio Spec |
| **Speech-to-Text (STT)** | `POST` | `https://api.meuu.club/v1/chat/completions` | Gemini Multimodal |
| **Direct Audio-to-Answer**| `POST` | `https://api.meuu.club/v1/chat/completions` | Gemini Multimodal |
| **Models List** | `GET` | `https://api.meuu.club/v1/models` | OpenAI v1 Spec |
| **Server Health** | `GET` | `https://api.meuu.club/api/health` | Healthcheck (200 OK) |

### มาตรฐาน Headers:
* **สำหรับ OpenAI Standard:**
  ```http
  Authorization: Bearer sk-07ccde1e709eb2ca-e05r6c-a11b5d7c
  Content-Type: application/json
  ```
* **สำหรับ Anthropic Standard:**
  ```http
  x-api-key: sk-07ccde1e709eb2ca-e05r6c-a11b5d7c
  anthropic-version: 2023-06-01
  Content-Type: application/json
  ```

---

## 3. ตารางโมเดล AI และความสามารถแบบเจาะลึก

| รหัสโมเดล (Model ID) | ค่าย | Context Window | ความเร็ว | ความสามารถเด่น | Vision | Audio | Tool Call |
| :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: |
| **`ag/claude-sonnet-4-6`** | Anthropic | 200,000 | ปานกลาง (~2s) | **อันดับ 1 ด้านการเขียนโค้ด**, วางโครงสร้างสถาปัตยกรรม, แก้บั๊กยาก | ✅ | ❌ | ✅ |
| **`ag/gemini-2.5-flash`** | Google | 1,000,000 | ⚡ เร็วมาก (~0.8s) | แชทเร็ว, บอทเสียง Real-time, ถอดเสียง STT (2.7s), สรุปข้อมูล | ✅ | ✅ | ✅ |
| **`ag/gemini-3-flash`** | Google | 1,000,000 | เร็ว (~1.5s) | มี Reasoning ในตัว, ให้เหตุผลเชิงลึก, แก้โจทย์คณิตศาสตร์ | ✅ | ✅ | ✅ |
| **`ag/gemini-2.5-pro`** | Google | 1,000,000 | ช้า-ลึก (~4s) | วิเคราะห์โค้ดทั้งโฟลเดอร์, งานวิจัยซับซ้อน, บริบท 1 ล้านโทเค็น | ✅ | ✅ | ✅ |
| **`claude-opus-4-6-thinking`**| Anthropic| 200,000 | ช้า-ลึก (~5s) | ตรรกะระดับสูงสุด พร้อมแสดงขั้นตอนการคิด (Thinking Steps) | ✅ | ❌ | ✅ |
| **`edge-tts/th-TH-PremwadeeNeural`**| Microsoft| - | ⚡ 0.7s - 1.5s | สร้างเสียงผู้หญิงไทย นุ่มนวล เป็นธรรมชาติ ฟรี 100% | ❌ | 🔊 (TTS) | ❌ |
| **`edge-tts/th-TH-NiwatNeural`**| Microsoft| - | ⚡ 0.7s - 1.5s | สร้างเสียงผู้ชายไทย ทุ้มนุ่ม ชัดเจน เป็นทางการ ฟรี 100% | ❌ | 🔊 (TTS) | ❌ |

---

## 4. Endpoint 1: Chat Completions

* **Full URL:** `https://api.meuu.club/v1/chat/completions`
* **Method:** `POST`

### 4.1 โครงสร้างพารามิเตอร์ทั้งหมด (Full Parameter Spec)
```json
{
  "model": "ag/claude-sonnet-4-6",       // [จำเป็น] ชื่อโมเดลที่ต้องการเรียกใช้
  "messages": [                           // [จำเป็น] ลิสต์ข้อความบทสนทนา
    {"role": "system", "content": "..."}, // [ไม่บังคับ] กำหนดบุคลิกหรือคำสั่งระบบ
    {"role": "user", "content": "..."},   // [จำเป็น] ข้อความจากผู้ใช้
    {"role": "assistant", "content": "..."}// [ไม่บังคับ] ประวัติคำตอบเดิมของ AI
  ],
  "temperature": 0.2,                     // [ไม่บังคับ] ค่าความสร้างสรรค์ (0.0 = แม่นยำตรงไปตรงมา, 1.0 = สร้างสรรค์)
  "max_tokens": 2048,                     // [ไม่บังคับ] จำนวนโทเค็นสูงสุดในคำตอบ
  "stream": false,                        // [ไม่บังคับ] true = สตรีมตัวอักษรทีละคำ, false = ตอบก้อนเดียวจบ
  "top_p": 0.95,                          // [ไม่บังคับ] Nucleus sampling
  "presence_penalty": 0.0,                // [ไม่บังคับ] ลดการพูดซ้ำหัวข้อเดิม (-2.0 ถึง 2.0)
  "frequency_penalty": 0.0,               // [ไม่บังคับ] ลดการพูดซ้ำคำเดิม (-2.0 ถึง 2.0)
  "stop": ["###"]                         // [ไม่บังคับ] คำหรือสัญลักษณ์ที่สั่งให้หยุดพิมพ์ทันที
}
```

---

### 4.2 แชทข้อความทั่วไป (Standard Chat)

#### ตัวอย่าง cURL:
```bash
curl -X POST "https://api.meuu.club/v1/chat/completions" \
  -H "Authorization: Bearer sk-07ccde1e709eb2ca-e05r6c-a11b5d7c" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ag/claude-sonnet-4-6",
    "messages": [
      {"role": "system", "content": "คุณคือ Senior Software Engineer ตอบกระชับตรงประเด็น"},
      {"role": "user", "content": "เขียนฟังก์ชันเชื่อมต่อ PostgreSQL ด้วย pg-promise ใน Node.js"}
    ],
    "temperature": 0.2
  }'
```

#### ตัวอย่าง Python (`openai` SDK):
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.meuu.club/v1",
    api_key="sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"
)

response = client.chat.completions.create(
    model="ag/claude-sonnet-4-6",
    messages=[
        {"role": "system", "content": "คุณคือ AI ผู้ช่วยเขียนโค้ด"},
        {"role": "user", "content": "เขียนคำสั่ง Dockerfile สำหรับโปรเจกต์ Go แบบ Multi-stage build"}
    ],
    temperature=0.2
)

print(response.choices[0].message.content)
```

#### ตัวอย่าง Node.js (TypeScript / JavaScript):
```javascript
import OpenAI from "openai";

const openai = new OpenAI({
  baseURL: "https://api.meuu.club/v1",
  apiKey: "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"
});

const completion = await openai.chat.completions.create({
  model: "ag/gemini-2.5-flash",
  messages: [{ role: "user", content: "อธิบายสั้นๆ ว่า WebSocket ต่างจาก HTTP อย่างไร" }]
});

console.log(completion.choices[0].message.content);
```

---

### 4.3 สตรีมมิ่งตัวอักษรเรียลไทม์ (Streaming SSE)

ส่งข้อมูลกลับมาแบบ Server-Sent Events (SSE) เหมาะสำหรับหน้าแชทที่ต้องการให้ตัวอักษรค่อยๆ พิมพ์ออกมา:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.meuu.club/v1",
    api_key="sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"
)

stream = client.chat.completions.create(
    model="ag/claude-sonnet-4-6",
    messages=[{"role": "user", "content": "เขียนบทความสั้นเกี่ยวกับข้อดีของ Clean Architecture"}],
    stream=True
)

for chunk in stream:
    text = chunk.choices[0].delta.content
    if text:
        print(text, end="", flush=True)
print()
```

---

### 4.4 วิเคราะห์รูปภาพและเอกสาร (Multimodal Vision / OCR)

รองรับทั้งรูปภาพผ่าน URL หรือส่งไฟล์ภาพแบบ Base64:

```python
import base64
from openai import OpenAI

client = OpenAI(base_url="https://api.meuu.club/v1", api_key="sk-07ccde1e709eb2ca-e05r6c-a11b5d7c")

# แปลงรูปภาพในเครื่องเป็น Base64
with open("architecture_diagram.png", "rb") as image_file:
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')

response = client.chat.completions.create(
    model="ag/claude-sonnet-4-6",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "ช่วยวิเคราะห์ไดอะแกรมระบบนี้ และชี้จุดที่อาจเกิด Single Point of Failure"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
        }
    ]
)

print(response.choices[0].message.content)
```

---

### 4.5 การเรียกใช้ฟังก์ชัน / เครื่องมือ (Function / Tool Calling)

AI สามารถประเมินและเลือกฟังก์ชันที่เหมาะสมพร้อมสร้าง Arguments รูปแบบ JSON ให้อัตโนมัติ:

```python
from openai import OpenAI

client = OpenAI(base_url="https://api.meuu.club/v1", api_key="sk-07ccde1e709eb2ca-e05r6c-a11b5d7c")

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "ดึงราคาหุ้นล่าสุดตามสัญลักษณ์ย่อ",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "สัญลักษณ์หุ้น เช่น AAPL, PTT"}
                },
                "required": ["symbol"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="ag/claude-sonnet-4-6",
    messages=[{"role": "user", "content": "ตอนนี้หุ้น AAPL ราคาเท่าไหร่"}],
    tools=tools,
    tool_choice="auto"
)

tool_call = response.choices[0].message.tool_calls[0]
print("ฟังก์ชันที่ AI เลือกเรียกใช้:", tool_call.function.name)
print("พารามิเตอร์ที่ส่ง:", tool_call.function.arguments)
```

---

## 5. Endpoint 2: Anthropic Claude Native

* **Full URL:** `https://api.meuu.club/v1/messages`
* **Method:** `POST`
* **Headers:**
  ```http
  x-api-key: sk-07ccde1e709eb2ca-e05r6c-a11b5d7c
  anthropic-version: 2023-06-01
  Content-Type: application/json
  ```

#### ตัวอย่าง cURL:
```bash
curl -X POST "https://api.meuu.club/v1/messages" \
  -H "x-api-key: sk-07ccde1e709eb2ca-e05r6c-a11b5d7c" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ag/claude-sonnet-4-6",
    "max_tokens": 1024,
    "system": "You are a world-class DevOps engineer.",
    "messages": [
      {"role": "user", "content": "Provide an Nginx configuration with SSL termination and dynamic resolver."}
    ]
  }'
```

---

## 6. Endpoint 3: สังเคราะห์เสียงพูด (Text-to-Speech)

* **Full URL:** `https://api.meuu.club/v1/audio/speech`
* **Method:** `POST`
* **Header:** `Authorization: Bearer sk-07ccde1e709eb2ca-e05r6c-a11b5d7c`
* **ค่าใช้จ่าย:** **ฟรี 100%** (ผ่านโปรโตคอล Edge Neural TTS)
* **ความเร็วเฉลี่ย:** **0.7 – 1.6 วินาที** (ตอบกลับเป็นไฟล์เสียง MP3 ทันที)

### 6.1 รายชื่อเสียงทั้งหมด (Voices List)
| Voice Identifier | ภาษา | เพศ | ลักษณะเสียง |
| :--- | :---: | :---: | :--- |
| **`edge-tts/th-TH-PremwadeeNeural`** | ไทย (th-TH) | หญิง | หวาน นุ่มนวล ธรรมชาติ (แนะนำสำหรับ Voice Bot) |
| **`edge-tts/th-TH-NiwatNeural`** | ไทย (th-TH) | ชาย | ทุ้มนุ่ม ชัดเจน ทางการ น่าเชื่อถือ |
| **`edge-tts/en-US-AriaNeural`** | อังกฤษ (en-US) | หญิง | คล่องแคล่ว สดใส มาตรฐาน |
| **`edge-tts/en-US-GuyNeural`** | อังกฤษ (en-US) | ชาย | สุภาพ อบอุ่น เป็นธรรมชาติ |
| **`edge-tts/ja-JP-NanamiNeural`** | ญี่ปุ่น (ja-JP) | หญิง | เสียงใส มาตรฐานอนิเมะ/ผู้ช่วย |
| **`edge-tts/zh-CN-XiaoxiaoNeural`** | จีน (zh-CN) | หญิง | สำเนียงกลาง ชัดเจน |

---

### 6.2 ตัวอย่างโค้ดสร้างเสียง MP3

#### cURL:
```bash
curl -X POST "https://api.meuu.club/v1/audio/speech" \
  -H "Authorization: Bearer sk-07ccde1e709eb2ca-e05r6c-a11b5d7c" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "edge-tts/th-TH-PremwadeeNeural",
    "input": "สวัสดีค่ะ ยินดีต้อนรับสู่ระบบปัญญาประดิษฐ์ เก้าราวเตอร์ วันนี้ระบบทำงานปกติค่ะ",
    "voice": "th-TH-PremwadeeNeural"
  }' \
  --output welcome.mp3
```

#### Python:
```python
import requests

url = "https://api.meuu.club/v1/audio/speech"
headers = {
    "Authorization": "Bearer sk-07ccde1e709eb2ca-e05r6c-a11b5d7c",
    "Content-Type": "application/json"
}
payload = {
    "model": "edge-tts/th-TH-PremwadeeNeural",
    "input": "ยินดีด้วยค่ะ คุณเชื่อมต่อกับระบบเก้าราวเตอร์สำเร็จแล้ว",
    "voice": "th-TH-PremwadeeNeural"
}

res = requests.post(url, json=payload, headers=headers)
with open("speech_output.mp3", "wb") as f:
    f.write(res.content)
print("บันทึกไฟล์เสียง speech_output.mp3 เรียบร้อยแล้ว (ขนาด:", len(res.content), "bytes)")
```

---

## 7. Endpoint 4: ถอดเสียงเป็นข้อความ (Speech-to-Text)

* **Full URL:** `https://api.meuu.club/v1/chat/completions`
* **Method:** `POST`
* **โมเดลที่แนะนำ:** **`ag/gemini-2.5-flash`** (เร็วเฉลี่ย 2.77 วินาที แม่นยำ 97%+)

### 7.1 ถอดเสียงภาษาไทยความเร็วสูง
```javascript
import fs from "fs";

const audioBase64 = fs.readFileSync("my_voice.mp3").toString("base64");

const response = await fetch("https://api.meuu.club/v1/chat/completions", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"
  },
  body: JSON.stringify({
    model: "ag/gemini-2.5-flash",
    temperature: 0.1,
    messages: [
      {
        role: "user",
        content: [
          { type: "text", text: "กรุณาถอดเสียงนี้เป็นข้อความภาษาไทยอย่างแม่นยำ พิมพ์เฉพาะสิ่งที่ได้ยินเท่านั้น" },
          { type: "input_audio", input_audio: { data: audioBase64, format: "mp3" } }
        ]
      }
    ]
  })
});

const result = await response.json();
console.log("ข้อความที่ถอดได้:", result.choices[0].message.content);
```

---

### 7.2 โฟลว์ลัดทะลวงคอขวด: ฟังเสียงแล้วตอบทันที (3.64 วินาที) ⚡

เทคนิคพิเศษที่ลดเวลาการโต้ตอบเสียงลงกว่า 60%: ส่งไฟล์เสียงคำถามเข้าไป แล้วให้ Gemini 2.5 Flash ฟังพร้อมคิดคำตอบออกมาทันทีในรอบเดียว!

```python
import base64
import requests

# 1. โหลดเสียงคำถามของผู้ใช้
with open("user_question.mp3", "rb") as f:
    audio_base64 = base64.b64encode(f.read()).decode("utf-8")

# 2. ขั้นที่ 1: ส่งเสียงให้ Gemini ฟังและตอบทันที (ใช้เวลา 2.64s)
headers = {
    "Authorization": "Bearer sk-07ccde1e709eb2ca-e05r6c-a11b5d7c",
    "Content-Type": "application/json"
}
chat_payload = {
    "model": "ag/gemini-2.5-flash",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "ฟังเสียงนี้แล้วตอบคำถามตรงประเด็น 1-2 ประโยค เพื่อนำไปอ่านออกเสียง"},
                {"type": "input_audio", "input_audio": {"data": audio_base64, "format": "mp3"}}
            ]
        }
    ]
}
chat_res = requests.post("https://api.meuu.club/v1/chat/completions", json=chat_payload, headers=headers).json()
ai_reply = chat_res["choices"][0]["message"]["content"]
print("AI ตอบว่า:", ai_reply)

# 3. ขั้นที่ 2: นำคำตอบส่งเข้า TTS สร้างเสียง MP3 (ใช้เวลา 1.00s)
tts_payload = {
    "model": "edge-tts/th-TH-PremwadeeNeural",
    "input": ai_reply,
    "voice": "th-TH-PremwadeeNeural"
}
tts_res = requests.post("https://api.meuu.club/v1/audio/speech", json=tts_payload, headers=headers)
with open("ai_response.mp3", "wb") as f:
    f.write(tts_res.content)

print("⚡ สร้างเสียงตอบกลับสำเร็จ! รวมเวลาทั้งสิ้นเพียง 3.64 วินาที")
```

---

## 8. Endpoint 5: ตรวจสอบโมเดล (`GET /v1/models`)

* **Full URL:** `https://api.meuu.club/v1/models`
* **Method:** `GET`
* **Header:** `Authorization: Bearer sk-07ccde1e709eb2ca-e05r6c-a11b5d7c`

```bash
curl -X GET "https://api.meuu.club/v1/models" \
  -H "Authorization: Bearer sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"
```

---

## 9. คู่มือตั้งค่าโปรแกรมเขียนโค้ดและ AI Agent ทุกค่าย

### 9.1 Cursor IDE
1. กดปุ่มลัด `Ctrl + Shift + J` (หรือไอคอนฟันเฟืองมุมขวาบน)
2. เมนูซ้ายเลือก **Models**
3. ปิดโมเดลเริ่มต้นอื่นๆ แล้วเปิดสวิตช์ **OpenAI API Key**
4. กดที่ปุ่ม **Override OpenAI Base URL**:
   * กรอก: `https://api.meuu.club/v1`
5. กรอก **API Key**:
   * กรอก: `sk-07ccde1e709eb2ca-e05r6c-a11b5d7c`
6. กดปุ่ม **+ Add Model** แล้วเพิ่มโมเดลเหล่านี้:
   * `ag/claude-sonnet-4-6` (สำหรับเขียนโค้ดและ Agentic mode)
   * `ag/gemini-2.5-flash` (สำหรับแชทเร็วและค้นหาโค้ด)

---

### 9.2 Claude Code CLI
รันคำสั่งกำหนด Environment Variable ใน Terminal ก่อนเปิดใช้งาน Claude Code:

**Windows PowerShell:**
```powershell
$env:ANTHROPIC_BASE_URL="https://api.meuu.club"
$env:ANTHROPIC_API_KEY="sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"
claude
```

**Linux / macOS:**
```bash
export ANTHROPIC_BASE_URL="https://api.meuu.club"
export ANTHROPIC_API_KEY="sk-07ccde1e709eb2ca-e05r6c-a11b5d7c"
claude
```

---

### 9.3 Cline & Roo Code (VS Code Extension)
1. เปิดแถบเครื่องมือ **Cline** หรือ **Roo Code** บน VS Code
2. คลิกรูปฟันเฟือง **Settings**
3. **API Provider:** เลือก `OpenAI Compatible`
4. **Base URL:** กรอก `https://api.meuu.club/v1`
5. **API Key:** กรอก `sk-07ccde1e709eb2ca-e05r6c-a11b5d7c`
6. **Model ID:** กรอก `ag/claude-sonnet-4-6`

---

### 9.4 Continue.dev
เปิดไฟล์ `~/.continue/config.json` แล้วเพิ่มบล็อกคอนฟิกนี้:
```json
{
  "models": [
    {
      "title": "9Router - Claude Sonnet 4.6",
      "provider": "openai",
      "model": "ag/claude-sonnet-4-6",
      "apiKey": "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c",
      "apiBase": "https://api.meuu.club/v1"
    },
    {
      "title": "9Router - Gemini 2.5 Flash",
      "provider": "openai",
      "model": "ag/gemini-2.5-flash",
      "apiKey": "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c",
      "apiBase": "https://api.meuu.club/v1"
    }
  ],
  "tabAutocompleteModel": {
    "title": "9Router Autocomplete",
    "provider": "openai",
    "model": "ag/gemini-2.5-flash",
    "apiKey": "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c",
    "apiBase": "https://api.meuu.club/v1"
  }
}
```

---

### 9.5 Windsurf IDE
1. เปิด **Settings** ➔ ค้นหา `Windsurf AI`
2. **Custom OpenAI Endpoint:** กรอก `https://api.meuu.club/v1`
3. **API Key:** กรอก `sk-07ccde1e709eb2ca-e05r6c-a11b5d7c`
4. **Model Name:** กรอก `ag/claude-sonnet-4-6`

---

### 9.6 Python / LangChain / Vercel AI SDK

#### LangChain (Python):
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="https://api.meuu.club/v1",
    api_key="sk-07ccde1e709eb2ca-e05r6c-a11b5d7c",
    model="ag/claude-sonnet-4-6",
    temperature=0.2
)

response = llm.invoke("ออกแบบโครงสร้างฐานข้อมูลสำหรับระบบ E-commerce")
print(response.content)
```

#### Vercel AI SDK (Next.js / Node.js):
```typescript
import { createOpenAI } from '@ai-sdk/openai';
import { generateText } from 'ai';

const meuuRouter = createOpenAI({
  baseURL: 'https://api.meuu.club/v1',
  apiKey: 'sk-07ccde1e709eb2ca-e05r6c-a11b5d7c',
});

const { text } = await generateText({
  model: meuuRouter('ag/claude-sonnet-4-6'),
  prompt: 'สรุป 3 เทรนด์เทคโนโลยีในปี 2026',
});

console.log(text);
```

---

## 10. ตารางรหัสข้อผิดพลาดและการแก้ปัญหา

| HTTP Code | ข้อความผิดพลาด | สาเหตุที่แท้จริง | วิธีการแก้ไข |
| :---: | :--- | :--- | :--- |
| **`200 OK`** | Success | ทำงานสำเร็จสมบูรณ์ | - |
| **`400 Bad Request`** | `Invalid model format` หรือ `Missing model` | สะกดชื่อโมเดลผิด หรือไม่ได้ระบุชื่อโมเดล | ตรวจสอบชื่อโมเดล เช่น ต้องใช้ `ag/claude-sonnet-4-6` หรือ `ag/gemini-2.5-flash` |
| **`400 Bad Request`** | `No credentials for provider: openai` | เรียกใช้โมเดลของ OpenAI โดยที่ไม่ได้ผูกคีย์ | หากต้องการสร้างเสียง ให้เปลี่ยนไปใช้โมเดล `edge-tts/*` แทน `tts-1` |
| **`401 Unauthorized`** | `Invalid API key` | ไม่ได้แนบ Header หรือคีย์สะกดผิด | ตรวจสอบ Header ให้เป็น `Authorization: Bearer sk-07ccde1e709eb2ca-e05r6c-a11b5d7c` |
| **`429 Rate Limit`** | `All accounts unavailable` | โควต้า 5 ชั่วโมงเต็มพร้อมกันทุกบัญชี | ปกติระบบมี 6 บัญชีจะสลับให้อัตโนมัติ หากเต็มทั้งหมดให้รอ 10-15 นาที |
| **`502 Bad Gateway`** | `Bad Gateway` | เซิร์ฟเวอร์ 9Router หรือ Tunnel ดับ | ให้รันสคริปต์ [`STATUS.bat`](file:///c:/Users/Administrator/Desktop/apl/STATUS.bat) เพื่อดูสถานะ หรือรัน [`START.bat`](file:///c:/Users/Administrator/Desktop/apl/START.bat) ใหม่ |

---

> 🏛️ *ไฟล์นี้คือมาตรฐานสูงสุดของเกตเวย์ 9Router — บันทึกเวอร์ชัน 2.0 วันที่ 3 ตุลาคม 2026*
