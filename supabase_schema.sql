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
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_uploads_date ON uploads(upload_date);
CREATE INDEX IF NOT EXISTS idx_uploads_created_at ON uploads(created_at);

-- ============================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================

-- Allow all operations for all users (public access)
-- You can adjust this based on your security requirements
CREATE POLICY "Enable all operations for all users" ON uploads
    FOR ALL USING (true);
