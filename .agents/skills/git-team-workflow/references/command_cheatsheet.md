# Git Command Cheatsheet (plain language)

A copy-pasteable reference. Grouped in the order you'd actually use them.

## เริ่มงานใหม่ / Start new work
```
git checkout main         # กลับไป branch หลัก / go to the main branch
git pull origin main      # ดึงของล่าสุดจาก GitHub / get latest changes from GitHub
git checkout -b feature/ชื่องาน   # สร้าง branch ใหม่สำหรับงานนี้ / create + switch to a new branch
```

## ระหว่างทำงาน / While working
```
git status     # ดูว่าไฟล์ไหนเปลี่ยนไปบ้าง / see what files changed
git diff       # ดูว่าเปลี่ยนอะไรไปบ้างในไฟล์ / see exact line changes
```

## บันทึกงาน / Save your work
```
git add .                          # เตรียมทุกไฟล์ที่แก้ / stage all changed files
git add <file>                     # เตรียมเฉพาะไฟล์นั้น / stage one file
git commit -m "อธิบายสั้นๆ ว่าทำอะไร"   # บันทึก / save a checkpoint
```

## ส่งขึ้น GitHub / Send to GitHub
```
git push -u origin feature/ชื่องาน   # push ครั้งแรกของ branch นี้ / first push on this branch
git push                             # push ครั้งต่อไป / later pushes
```

## รวมงานเข้า main / Bring work into main
เปิดลิงก์ที่ git ให้มาหลัง push (รูปแบบ `https://github.com/<org>/<repo>/pull/new/<branch>`) เพื่อสร้าง Pull Request (PR) ให้เพื่อนรีวิวแล้วกด merge บนเว็บ

หลัง merge เสร็จ:
```
git checkout main
git pull origin main
```

## เมื่อมีปัญหา / When something goes wrong

**ยกเลิกการแก้ไขที่ยังไม่ add** — Undo edits not yet staged:
```
git restore <file>
```

**ยกเลิกการ add (แต่ยังไม่ commit)** — Un-stage without losing edits:
```
git restore --staged <file>
```

**เก็บงานค้างไว้ชั่วคราวเพื่อสลับ branch** — Stash unfinished work:
```
git stash
git stash pop     # เอากลับมาทีหลัง / bring it back later
```

**เจอ merge conflict** — When git can't auto-merge:
1. เปิดไฟล์ที่ขึ้น conflict มองหา `<<<<<<<`, `=======`, `>>>>>>>`
2. แก้ไฟล์ให้เหลือโค้ดที่ถูกต้อง แล้วลบเครื่องหมายพวกนี้ออก
3. รัน:
```
git add <file>
git commit
```

**clone repo ครั้งแรก** — First time getting the project:
```
git clone <URL>
```

**โฟลเดอร์ชื่อซ้ำตอน clone** — "already exists" error:
```
rm -rf <folder-name>   # ลบโฟลเดอร์เก่า (เช็คกับเจ้าของงานก่อนลบ)
git clone <URL>
```
หรือถ้ามีโฟลเดอร์อยู่แล้วและอยากได้ของล่าสุด แค่ `cd` เข้าไปแล้ว `git pull origin main` แทนการ clone ใหม่

**ดูประวัติ commit** — See commit history:
```
git log --oneline
```

**ดู branch ทั้งหมด** — List branches:
```
git branch
```

**กันไฟล์ไม่ให้ถูก track** — Keep files out of git (secrets, dependencies):
สร้างไฟล์ `.gitignore` ที่ root ของโปรเจกต์ แล้วใส่ชื่อไฟล์/โฟลเดอร์ทีละบรรทัด เช่น:
```
node_modules/
.env
.DS_Store
```
