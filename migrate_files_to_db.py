#!/usr/bin/env python3
"""
Script สำหรับย้ายไฟล์จากดิสก์ไปยัง Supabase database
"""

import os
import sys
from supabase_config import get_supabase

def migrate_files_to_database():
    """ย้ายไฟล์จากดิสก์ไปยัง Supabase database"""
    
    supabase = get_supabase()
    
    if not supabase.is_connected():
        print("ERROR: Cannot connect to Supabase")
        return
    
    print("Starting file migration to database...")
    
    try:
        # ดึงข้อมูลไฟล์ทั้งหมด
        result = supabase.supabase.table("uploads").select("*").execute()
        files = result.data or []
        
        if not files:
            print("No files to migrate")
            return
        
        migrated_count = 0
        skipped_count = 0
        
        for file_record in files:
            file_id = file_record["id"]
            stored_path = file_record["stored_path"]
            filename = file_record["orig_filename"]
            
            # ตรวจสอบว่ามี file_content อยู่แล้วหรือไม่
            if file_record.get("file_content"):
                print(f"Skipping {filename} (already in database)")
                skipped_count += 1
                continue
            
            # ตรวจสอบว่าไฟล์มีอยู่ในดิสก์หรือไม่
            if not os.path.exists(stored_path):
                print(f"Warning: File not found on disk: {filename}")
                continue
            
            # อ่านไฟล์จากดิสก์
            try:
                with open(stored_path, "rb") as f:
                    file_content = f.read()
                
                # คำนวณ metadata
                file_size = len(file_content)
                file_extension = os.path.splitext(filename)[1].lower()
                import mimetypes
                mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                import hashlib
                checksum = hashlib.md5(file_content).hexdigest()
                
                # อัพเดต record ใน database (แปลงเป็น base64)
                import base64
                update_data = {
                    "file_content": base64.b64encode(file_content).decode('utf-8'),
                    "file_size": file_size,
                    "file_type": file_extension,
                    "mime_type": mime_type,
                    "checksum": checksum
                }
                
                supabase.supabase.table("uploads").update(update_data).eq("id", file_id).execute()
                print(f"Migrated: {filename} ({file_size} bytes)")
                migrated_count += 1
                
            except Exception as e:
                print(f"Error migrating {filename}: {e}")
        
        print(f"\nMigration completed!")
        print(f"Migrated: {migrated_count} files")
        print(f"Skipped: {skipped_count} files")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate_files_to_database()
