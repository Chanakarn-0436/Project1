# Supabase Setup Guide

## 📋 Database Schema

ระบบใช้ Supabase database โดยมีตารางเดียว:

### Uploads Table
```sql
CREATE TABLE uploads (
    id BIGSERIAL PRIMARY KEY,
    upload_date TEXT NOT NULL,
    orig_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🚀 Setup Instructions

### 1. สร้าง Supabase Project
1. ไปที่ [https://supabase.com](https://supabase.com)
2. สร้างบัญชีและสร้าง project ใหม่
3. รอให้ database ถูกสร้างเสร็จ

### 2. สร้างตาราง
1. ไปที่ SQL Editor ใน Supabase dashboard
2. รัน SQL script จากไฟล์ `supabase_schema.sql`:

```bash
# คัดลอกเนื้อหาจากไฟล์ supabase_schema.sql และรันใน SQL Editor
```

หรือรันคำสั่งนี้โดยตรง:

```sql
-- สร้างตาราง uploads
CREATE TABLE IF NOT EXISTS uploads (
    id BIGSERIAL PRIMARY KEY,
    upload_date TEXT NOT NULL,
    orig_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- สร้าง indexes
CREATE INDEX IF NOT EXISTS idx_uploads_date ON uploads(upload_date);
CREATE INDEX IF NOT EXISTS idx_uploads_created_at ON uploads(created_at);

-- ตั้งค่า Row Level Security
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;

-- อนุญาตให้ทุกคนเข้าถึงได้ (สามารถปรับแต่งได้ตามความต้องการ)
CREATE POLICY "Enable all operations for all users" ON uploads
    FOR ALL USING (true);
```

### 3. ตั้งค่า Credentials

#### สำหรับ Local Development (Streamlit secrets)
สร้างไฟล์ `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key-here"
```

#### สำหรับ Production (Environment Variables)
ตั้งค่า environment variables:

```bash
export SUPABASE_URL="https://your-project-id.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key-here"
```

### 4. หา Credentials ของคุณ
1. ไปที่ Supabase dashboard
2. เลือก project ของคุณ
3. ไปที่ **Settings** → **API**
4. คัดลอก:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_ANON_KEY`

## 🔒 Security Notes

- Row Level Security (RLS) ถูกเปิดใช้งาน
- Policy ปัจจุบันอนุญาตให้ทุกคนเข้าถึงได้ (`FOR ALL USING (true)`)
- สำหรับ production ควรปรับแต่ง RLS policies ให้เข้มงวดมากขึ้น

### ตัวอย่าง Policy สำหรับ Authentication
```sql
-- ลบ policy เดิม
DROP POLICY IF EXISTS "Enable all operations for all users" ON uploads;

-- สร้าง policy ใหม่สำหรับ authenticated users
CREATE POLICY "Enable operations for authenticated users" ON uploads
    FOR ALL USING (auth.role() = 'authenticated');
```

## 📊 การใช้งาน

ระบบจะใช้ Supabase อัตโนมัติ หากไม่สามารถเชื่อมต่อได้ จะแสดงข้อความแจ้งเตือน:
- ✅ "Connected to Supabase Database" = เชื่อมต่อสำเร็จ
- ❌ "Cannot connect to Supabase Database" = เชื่อมต่อไม่สำเร็จ

## 🔧 Troubleshooting

### ไม่สามารถเชื่อมต่อ Supabase
1. ตรวจสอบว่า `SUPABASE_URL` และ `SUPABASE_ANON_KEY` ถูกต้อง
2. ตรวจสอบว่า Supabase project ยังทำงานอยู่
3. ตรวจสอบว่าตาราง `uploads` ถูกสร้างแล้ว

### RLS Policy ไม่ทำงาน
1. ตรวจสอบว่า RLS ถูกเปิดใช้งาน: `ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;`
2. ตรวจสอบว่ามี policy ที่อนุญาตการเข้าถึง
3. ลองปิด RLS ชั่วคราวเพื่อทดสอบ: `ALTER TABLE uploads DISABLE ROW LEVEL SECURITY;`

### ติดตั้ง Dependencies
```bash
pip install supabase
```

## 📝 Migration จาก SQLite

ถ้าคุณมีข้อมูลเดิมใน SQLite (`files.db`), สามารถ migrate ได้:

```python
import sqlite3
from supabase_config import get_supabase

# อ่านข้อมูลจาก SQLite
conn = sqlite3.connect('files.db')
cursor = conn.cursor()
cursor.execute("SELECT upload_date, orig_filename, stored_path, created_at FROM uploads")
rows = cursor.fetchall()

# ย้ายไปยัง Supabase
supabase = get_supabase()
for row in rows:
    upload_date, orig_filename, stored_path, created_at = row
    supabase.save_upload_record(upload_date, orig_filename, stored_path)

conn.close()
print(f"Migrated {len(rows)} records to Supabase")
```

## 🎉 เสร็จสิ้น!

หลังจากตั้งค่าเรียบร้อยแล้ว ระบบจะใช้ Supabase ในการจัดเก็บข้อมูลการอัปโหลดไฟล์ทั้งหมด

