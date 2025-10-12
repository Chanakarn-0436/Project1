-- ============================================
-- Supabase Database Schema for Network Monitoring
-- ============================================

-- Enable Row Level Security
ALTER TABLE IF EXISTS uploads ENABLE ROW LEVEL SECURITY;

-- ============================================
-- UPLOADS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS uploads (
    id BIGSERIAL PRIMARY KEY,
    upload_date TEXT NOT NULL,
    orig_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    storage_url TEXT, -- URL ในSupabase Storage (ถ้ามี)
    file_size BIGINT, -- ขนาดไฟล์ใน bytes
    file_type TEXT, -- ประเภทไฟล์ (zip, xlsx, txt, etc.)
    mime_type TEXT, -- MIME type
    checksum TEXT, -- MD5 checksum สำหรับตรวจสอบความสมบูรณ์
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_uploads_date ON uploads(upload_date);
CREATE INDEX IF NOT EXISTS idx_uploads_created_at ON uploads(created_at);
CREATE INDEX IF NOT EXISTS idx_uploads_file_type ON uploads(file_type);
CREATE INDEX IF NOT EXISTS idx_uploads_file_size ON uploads(file_size);

-- ============================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================

-- Allow all operations for all users (public access)
-- You can adjust this based on your security requirements
CREATE POLICY "Enable all operations for all users" ON uploads
    FOR ALL USING (true);
