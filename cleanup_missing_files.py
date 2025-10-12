#!/usr/bin/env python3
"""
Script สำหรับทำความสะอาดไฟล์ที่หายไปจากดิสก์ แต่ยังมีข้อมูลใน Supabase
สำหรับ Project1
"""

import os
import sys
from supabase_config import get_supabase

def cleanup_missing_files():
    """ลบข้อมูลไฟล์ที่ไม่มีอยู่จริงในดิสก์ออกจาก Supabase"""
    
    supabase = get_supabase()
    
    if not supabase.is_connected():
        print("ERROR: Cannot connect to Supabase")
        return
    
    print("Checking for missing files in Project1...")
    
    # ดึงข้อมูลทั้งหมดจาก Supabase
    try:
        result = supabase.supabase.table("uploads").select("*").execute()
        files = result.data or []
        
        if not files:
            print("OK: No files in database")
            return
        
        missing_files = []
        
        for file_record in files:
            file_path = file_record["stored_path"]
            file_id = file_record["id"]
            filename = file_record["orig_filename"]
            
            # ตรวจสอบว่าไฟล์มีอยู่จริงหรือไม่
            if not os.path.exists(file_path):
                missing_files.append((file_id, filename, file_path))
                print(f"Missing: {filename} (ID: {file_id})")
                print(f"  Path: {file_path}")
        
        if not missing_files:
            print("OK: All files exist on disk")
            return
        
        print(f"\nFound {len(missing_files)} missing files")
        
        # แสดงรายการไฟล์ที่หายไป
        print("\nMissing files:")
        for i, (file_id, filename, file_path) in enumerate(missing_files, 1):
            print(f"{i}. {filename}")
            print(f"   ID: {file_id}")
            print(f"   Path: {file_path}")
        
        # ถามว่าต้องการลบหรือไม่
        response = input("\nDo you want to remove these missing files from database? (y/N): ")
        
        if response.lower() in ['y', 'yes']:
            removed_count = 0
            
            for file_id, filename, file_path in missing_files:
                try:
                    # ลบจาก Supabase
                    supabase.supabase.table("uploads").delete().eq("id", file_id).execute()
                    print(f"Removed: {filename}")
                    removed_count += 1
                except Exception as e:
                    print(f"Failed to remove {filename}: {e}")
            
            print(f"\nSuccessfully removed {removed_count} missing files from database")
        else:
            print("Operation cancelled")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cleanup_missing_files()
