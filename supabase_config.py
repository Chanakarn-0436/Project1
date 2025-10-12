import os
import streamlit as st
from supabase import create_client, Client
from typing import Optional
from datetime import datetime
import hashlib
import mimetypes

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
    def save_upload_record(self, upload_date: str, orig_filename: str, stored_path: str, file_content: bytes = None) -> Optional[int]:
        """บันทึกข้อมูลการอัปโหลดไฟล์ (พร้อมเนื้อหาไฟล์ถ้ามี)"""
        if not self.is_connected():
            return None
        
        try:
            # คำนวณข้อมูลไฟล์
            file_size = len(file_content) if file_content else 0
            file_extension = os.path.splitext(orig_filename)[1].lower()
            mime_type = mimetypes.guess_type(orig_filename)[0] or "application/octet-stream"
            checksum = hashlib.md5(file_content).hexdigest() if file_content else None
            
            data = {
                "upload_date": upload_date,
                "orig_filename": orig_filename,
                "stored_path": stored_path,
                "file_content": file_content,
                "file_size": file_size,
                "file_type": file_extension,
                "mime_type": mime_type,
                "checksum": checksum,
                "created_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("uploads").insert(data).execute()
            if result.data:
                return result.data[0]["id"]
            return None
            
        except Exception as e:
            st.error(f"❌ Failed to save upload record: {e}")
            return None
    
    def get_file_content(self, file_id: int) -> Optional[bytes]:
        """ดึงเนื้อหาไฟล์จาก database"""
        if not self.is_connected():
            return None
        
        try:
            result = self.supabase.table("uploads").select("file_content, orig_filename, checksum").eq("id", file_id).execute()
            if result.data:
                file_record = result.data[0]
                file_content = file_record["file_content"]
                
                # ตรวจสอบ checksum ถ้ามี
                if file_content and file_record.get("checksum"):
                    calculated_checksum = hashlib.md5(file_content).hexdigest()
                    if calculated_checksum != file_record["checksum"]:
                        st.warning(f"⚠️ File integrity check failed for {file_record['orig_filename']}")
                
                return file_content
            return None
            
        except Exception as e:
            st.error(f"❌ Failed to get file content: {e}")
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
