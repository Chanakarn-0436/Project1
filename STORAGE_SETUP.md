# Supabase Storage Setup Guide

## 🎯 เป้าหมาย
ให้คนอื่นสามารถเข้าถึงและวิเคราะห์ไฟล์ได้จากที่ไหนก็ได้ ผ่าน Supabase Storage

## 📋 ขั้นตอนการตั้งค่า Supabase Storage

### 1. สร้าง Storage Bucket

1. เข้า Supabase Dashboard: https://app.supabase.com
2. เลือก Project ของคุณ
3. ไปที่ **Storage** ในเมนูซ้าย
4. คลิก **New Bucket**
5. กรอกข้อมูล:
   - **Name**: `uploads`
   - **Public bucket**: ✅ เลือก (ถ้าต้องการให้ทุกคนเข้าถึงได้)
   - **File size limit**: `104857600` (100MB)
6. คลิก **Create bucket**

### 2. ตั้งค่า Storage Policies (ถ้าเป็น Private Bucket)

ถ้าคุณไม่เลือก Public bucket ให้ตั้งค่า policies:

```sql
-- Allow anyone to upload files
CREATE POLICY "Allow public uploads"
ON storage.objects FOR INSERT
TO public
WITH CHECK (bucket_id = 'uploads');

-- Allow anyone to read files
CREATE POLICY "Allow public reads"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'uploads');

-- Allow anyone to delete files
CREATE POLICY "Allow public deletes"
ON storage.objects FOR DELETE
TO public
USING (bucket_id = 'uploads');
```

### 3. อัพเดต Environment Variables

เพิ่มใน `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "your-supabase-url"
SUPABASE_ANON_KEY = "your-anon-key"
STORAGE_BUCKET = "uploads"
```

### 4. รัน Migration

ไม่ต้องทำอะไร - ระบบจะใช้ Storage API โดยอัตโนมัติ

## 🎯 ข้อดีของ Supabase Storage

✅ **คนอื่นเข้าถึงได้** - ไฟล์เก็บบน cloud
✅ **รวดเร็ว** - ไม่มี timeout เหมือน database
✅ **ปลอดภัย** - มี authentication & authorization
✅ **ประหยัด** - Free tier: 1GB storage
✅ **CDN** - รองรับ CDN สำหรับไฟล์ขนาดใหญ่

## ⚠️ ข้อจำกัด Free Tier

- Storage: 1GB
- Bandwidth: 2GB/month
- File size limit: 50MB (default)

## 🔄 การทำงาน

```
Upload File
    ↓
Upload to Supabase Storage (cloud)
    ↓
Get Public URL
    ↓
Save URL + Metadata to Database
    ↓
Done! (คนอื่นดาวน์โหลดได้)
```

