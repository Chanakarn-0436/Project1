import os
import streamlit as st
from supabase import create_client, Client
from typing import Optional
from datetime import datetime

class SupabaseManager:
    """จัดการการเชื่อมต่อและใช้งาน Supabase Database"""
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        self._init_connection()
    
    def _init_connection(self):
        """เริ่มต้นการเชื่อมต่อ Supabase"""
        try:
            # ใช้ environment variables หรือ Streamlit secrets
            url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
            key = st.secrets.get("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")
            
            if not url or not key:
                # ไม่แสดง error ที่นี่ เพราะอาจทำให้หน้า UI รก
                # ให้เช็คที่ is_connected() แทน
                self.supabase = None
                return
            
            self.supabase = create_client(url, key)
            
        except Exception as e:
            # Silent fail - will check with is_connected()
            self.supabase = None
    
    def is_connected(self) -> bool:
        """ตรวจสอบว่ามีการเชื่อมต่อ Supabase หรือไม่"""
        return self.supabase is not None
    
    # ===== FILE MANAGEMENT =====
    def save_upload_record(self, upload_date: str, orig_filename: str, stored_path: str) -> Optional[int]:
        """บันทึกข้อมูลการอัปโหลดไฟล์"""
        if not self.is_connected():
            return None
        
        try:
            data = {
                "upload_date": upload_date,
                "orig_filename": orig_filename,
                "stored_path": stored_path,
                "created_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("uploads").insert(data).execute()
            if result.data:
                return result.data[0]["id"]
            return None
            
        except Exception as e:
            st.error(f"❌ Failed to save upload record: {e}")
            return None
    
    def get_files_by_date(self, upload_date: str) -> list:
        """ดึงรายการไฟล์ตามวันที่"""
        if not self.is_connected():
            return []
        
        try:
            result = self.supabase.table("uploads").select("id, orig_filename, stored_path").eq("upload_date", upload_date).execute()
            return result.data or []
        except Exception as e:
            st.error(f"❌ Failed to get files by date: {e}")
            return []
    
    def delete_file_record(self, file_id: int) -> bool:
        """ลบข้อมูลไฟล์"""
        if not self.is_connected():
            return False
        
        try:
            self.supabase.table("uploads").delete().eq("id", file_id).execute()
            return True
        except Exception as e:
            st.error(f"❌ Failed to delete file record: {e}")
            return False
    
    def get_dates_with_files(self) -> list:
        """ดึงรายการวันที่ที่มีไฟล์"""
        if not self.is_connected():
            return []
        
        try:
            result = self.supabase.table("uploads").select("upload_date").execute()
            if not result.data:
                return []
            
            # นับจำนวนไฟล์ต่อวัน
            date_counts = {}
            for row in result.data:
                date = row["upload_date"]
                date_counts[date] = date_counts.get(date, 0) + 1
            
            return [(date, count) for date, count in date_counts.items()]
        except Exception as e:
            st.error(f"❌ Failed to get dates with files: {e}")
            return []

# Global instance
supabase_manager = SupabaseManager()

def get_supabase() -> SupabaseManager:
    """Get global Supabase manager instance"""
    return supabase_manager
