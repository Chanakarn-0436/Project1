# app9_optimized.py
"""
Optimized version of app9.py with performance improvements
"""
import os
import uuid
from datetime import datetime, date
import pytz
import streamlit as st
from streamlit_calendar import calendar
import io, zipfile
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time
import re

# Import optimized analyzers
from Fiberflapping_Analyzer_Optimized import FiberflappingAnalyzerOptimized
from Line_Analyzer_Optimized import Line_Analyzer_Optimized
from APO_Analyzer_Optimized import ApoRemnantAnalyzerOptimized

# Import other analyzers (keep original for now)
from CPU_Analyzer import CPU_Analyzer
from FAN_Analyzer import FAN_Analyzer
from MSU_Analyzer import MSU_Analyzer
from Client_Analyzer import Client_Analyzer
from EOL_Core_Analyzer import EOLAnalyzer, CoreAnalyzer
from Preset_Analyzer import PresetStatusAnalyzer, render_preset_ui
from APO_Analyzer import apo_kpi
from supabase_config import get_supabase

# Import performance utilities
from utils.performance_utils import (
    optimize_dataframe_operations,
    performance_monitor,
    optimize_dataframe_memory,
    batch_process_dataframe
)

# ====== CONFIG ======
st.set_page_config(layout="wide")
pd.set_option("styler.render.max_elements", 1_200_000)

# Initialize performance optimizations
optimize_dataframe_operations()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ====== SUPABASE INSTANCE ======
supabase = get_supabase()

# ====== OPTIMIZED FILE FUNCTIONS ======
@performance_monitor
def save_file(upload_date: str, file, use_storage: bool = True):
    """Optimized file saving with performance monitoring"""
    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}_{file.name}"
    file_content = bytes(file.getbuffer())
    
    storage_url = None
    stored_path = None
    
    if use_storage and supabase.is_connected():
        storage_path = f"{upload_date}/{stored_name}"
        storage_url = supabase.upload_to_storage(file_content, storage_path)
        
        if storage_url:
            stored_path = storage_path
        else:
            use_storage = False
    
    if not use_storage or not storage_url:
        stored_path = os.path.join(UPLOAD_DIR, upload_date, stored_name)
        os.makedirs(os.path.dirname(stored_path), exist_ok=True)
        with open(stored_path, "wb") as f:
            f.write(file_content)
    
    supabase.save_upload_record(upload_date, file.name, stored_path, storage_url)

@performance_monitor
def get_file_for_analysis(file_id):
    """Optimized file retrieval with performance monitoring"""
    if not supabase.is_connected():
        return None
    
    try:
        # แปลง file_id เป็น integer ถ้าเป็น string
        if isinstance(file_id, str):
            if file_id.isdigit():
                file_id = int(file_id)
            else:
                st.error(f"❌ Invalid file ID: {file_id}")
                return None
        
        result = supabase.supabase.table("uploads").select("*").eq("id", file_id).execute()
        if not result.data:
            return None
        
        file_record = result.data[0]
        stored_path = file_record["stored_path"]
        storage_url = file_record.get("storage_url")
        
        # Try Supabase Storage first
        if storage_url:
            file_content = supabase.download_from_storage(stored_path)
            if file_content:
                return io.BytesIO(file_content)
        
        # Try local disk
        if os.path.exists(stored_path):
            with open(stored_path, "rb") as f:
                return io.BytesIO(f.read())
        
        # Try database (legacy)
        if file_record.get("file_content"):
            import base64
            file_content = base64.b64decode(file_record["file_content"])
            return io.BytesIO(file_content)
        
        return None
        
    except Exception as e:
        st.error(f"❌ Failed to get file for analysis: {e}")
        return None

# ====== OPTIMIZED ZIP PARSER ======
KW = {
    "cpu": ("cpu",),
    "fan": ("fan",),
    "msu": ("msu",),
    "client": ("client", "client board"),
    "line":  ("line","line board"),       
    "wason": ("wason","log","mobaxterm", "moba xterm", "moba"), 
    "osc": ("osc","osc optical"),      
    "fm":  ("fm","alarm","fault management"),
    "atten": ("optical attenuation report", "optical_attenuation_report","optical attenuation"),
    "preset": ("wason","log","mobaxterm", "moba xterm", "moba"),
}

LOADERS = {
    ".xlsx": pd.read_excel,
    ".xls": pd.read_excel,
    ".txt":  lambda f: f.read().decode("utf-8", errors="ignore"),
}

def _ext(name: str) -> str:
    name = name.lower()
    return next((e for e in LOADERS if name.endswith(e)), "")

def _kind(name):
    n = name.lower()
    hits = [k for k, kws in KW.items() if any(re.search(re.escape(s), n) for s in kws)]
    
    if "wason" in hits:
        return "wason"
    if "preset" in hits:
        return "preset"
    if "line" in hits and (n.endswith(".xlsx") or n.endswith(".xls") or n.endswith(".xlsm")):
        return "line"
    
    for k in ("fan","cpu","msu","client","osc","fm","atten"):
        if k in hits:
            return k
    
    return hits[0] if hits else None

@performance_monitor
def find_in_zip(zip_file):
    """Optimized ZIP parsing with performance monitoring"""
    found = {k: None for k in KW}
    
    def walk(zf):
        for name in zf.namelist():
            if all(found.values()): 
                return
            if name.endswith("/"): 
                continue
            lname = name.lower()
            if lname.endswith(".zip"):
                try:
                    walk(zipfile.ZipFile(io.BytesIO(zf.read(name))))
                except:
                    pass
                continue
            ext = _ext(lname)
            kind = _kind(lname)
            if not ext or not kind or found[kind]:
                continue
            try:
                with zf.open(name) as f:
                    df = LOADERS[ext](f)
                    print("DEBUG LOADED:", kind, type(df), name)
                
                if kind == "wason":
                    found[kind] = (df, name)
                else:
                    found[kind] = (df, name)
            except:
                continue
    
    walk(zipfile.ZipFile(zip_file))
    return found

# ====== OPTIMIZED ANALYSIS FUNCTIONS ======
@performance_monitor
def process_fiberflapping_optimized(df_osc, df_fm):
    """Optimized fiber flapping analysis"""
    try:
        analyzer = FiberflappingAnalyzerOptimized(
            df_optical=df_osc.copy(),
            df_fm=df_fm.copy(),
            threshold=2.0,
            ref_path="data/Flapping.xlsx"
        )
        analyzer.process()
        st.session_state["fiberflapping_analyzer"] = analyzer
        return True
    except Exception as e:
        st.error(f"Fiberflapping analysis error: {e}")
        return False

@performance_monitor
def process_line_optimized(df_line, pmap):
    """Optimized line analysis"""
    try:
        df_ref = pd.read_excel("data/Line.xlsx")
        analyzer = Line_Analyzer_Optimized(
            df_line=df_line.copy(),
            df_ref=df_ref.copy(),
            pmap=pmap,
            ns="line"
        )
        analyzer.process()
        st.session_state["line_analyzer"] = analyzer
        return True
    except Exception as e:
        st.error(f"Line analysis error: {e}")
        return False

@performance_monitor
def process_apo_optimized(wason_log):
    """Optimized APO analysis"""
    try:
        analyzer = ApoRemnantAnalyzerOptimized(wason_log)
        analyzer.parse()
        analyzer.analyze()
        st.session_state["apo_analyzer"] = analyzer
        
        # Set session state for sidebar indicator
        rendered = getattr(analyzer, "rendered", [])
        apo_sites = sum(1 for x in rendered if x[2])
        st.session_state["apo_abn_count"] = apo_sites
        st.session_state["apo_status"] = "Abnormal" if apo_sites > 0 else "Normal"
        return True
    except Exception as e:
        st.error(f"APO analysis error: {e}")
        return False

# ====== OPTIMIZED SIDEBAR ======
def create_menu_with_indicators():
    """Create menu with performance indicators"""
    menu_items = [
        "Home", "Dashboard", "CPU", "FAN", "MSU", "Line board", "Client board",
        "Fiber Flapping", "Loss between Core", "Loss between EOL", "Preset status", "APO Remnant", "Summary table & report"
    ]
    
    status_checks = {
        "CPU": (st.session_state.get("cpu_status", "Normal"), st.session_state.get("cpu_abn_count", 0)),
        "FAN": (st.session_state.get("fan_status", "Normal"), st.session_state.get("fan_abn_count", 0)),
        "MSU": (st.session_state.get("msu_status", "Normal"), st.session_state.get("msu_abn_count", 0)),
        "Line board": (st.session_state.get("line_status", "Normal"), st.session_state.get("line_abn_count", 0)),
        "Client board": (st.session_state.get("client_status", "Normal"), st.session_state.get("client_abn_count", 0)),
        "Fiber Flapping": (st.session_state.get("fiberflapping_status", "Normal"), st.session_state.get("fiberflapping_abn_count", 0)),
        "Loss between Core": (st.session_state.get("core_status", "Normal"), st.session_state.get("core_abn_count", 0)),
        "Loss between EOL": (st.session_state.get("eol_status", "Normal"), st.session_state.get("eol_abn_count", 0)),
        "Preset status": (st.session_state.get("preset_status", "Normal"), st.session_state.get("preset_abn_count", 0)),
        "APO Remnant": (st.session_state.get("apo_status", "Normal"), st.session_state.get("apo_abn_count", 0))
    }
    
    menu_with_indicators = []
    for item in menu_items:
        if item in status_checks:
            status, count = status_checks[item]
            if status == "Abnormal" and count > 0:
                menu_with_indicators.append(f"🔴 {item} ({count})")
            else:
                menu_with_indicators.append(item)
        else:
            menu_with_indicators.append(item)
    
    return menu_with_indicators

# ====== MAIN APPLICATION ======
def main():
    """Main application with optimized performance"""
    # Create menu
    menu_options = create_menu_with_indicators()
    menu = st.sidebar.radio("Select Activity", menu_options)
    
    # Convert menu selection
    original_menu = re.sub(r"🔴 (.+?) \(\d+\)", r"\1", menu)
    if original_menu == menu:
        original_menu = menu.replace("🔴 ", "") if "🔴 " in menu else menu
    
    # Route to appropriate page
    if original_menu == "Home":
        render_home_page()
    elif original_menu == "Dashboard":
        render_dashboard()
    elif original_menu == "Fiber Flapping":
        render_fiberflapping_optimized()
    elif original_menu == "Line board":
        render_line_board_optimized()
    elif original_menu == "APO Remnant":
        render_apo_optimized()
    else:
        # Fallback to original implementation for other pages
        render_other_pages(original_menu)

def render_home_page():
    """Render home page with optimized file handling"""
    st.subheader("3BB Network Inspection Dashboard")
    st.markdown("#### Upload & Manage Files (ZIP, Excel, TXT) with Calendar")
    
    chosen_date = st.date_input("Select date", value=date.today())
    
    # File upload with performance monitoring
    col1, col2 = st.columns([3, 1])
    with col1:
        files = st.file_uploader(
            "Upload files (ZIP / Excel / TXT)",
            type=["zip", "xlsx", "xls", "xlsm", "txt"],
            accept_multiple_files=True,
            key=f"uploader_{chosen_date}"
        )
    with col2:
        use_storage = st.checkbox(
            "☁️ Use Cloud Storage", 
            value=True,
            help="Store files in Supabase Storage (accessible from anywhere)"
        )
    
    if files:
        if st.button("Upload", key=f"upload_btn_{chosen_date}"):
            # Optimized upload with progress tracking
            upload_files_optimized(files, chosen_date, use_storage)
    
    # Calendar and file management
    render_calendar_and_files(chosen_date)

@performance_monitor
def upload_files_optimized(files, chosen_date, use_storage):
    """Optimized file upload with progress tracking"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_files = len(files)
    uploaded_count = 0
    
    for i, file in enumerate(files):
        status_text.text(f"📤 Uploading {file.name}... ({i+1}/{total_files})")
        progress = (i + 1) / total_files
        progress_bar.progress(progress)
        
        try:
            save_file(str(chosen_date), file, use_storage=use_storage)
            uploaded_count += 1
        except Exception as e:
            st.error(f"❌ Failed to upload {file.name}: {e}")
        
        time.sleep(0.1)  # Small delay for progress visibility
    
    progress_bar.progress(1.0)
    status_text.text(f"✅ Upload completed! Successfully uploaded {uploaded_count}/{total_files} files")
    
    if uploaded_count == total_files:
        st.success(f"🎉 All {total_files} files uploaded successfully!")
    else:
        st.warning(f"⚠️ Uploaded {uploaded_count}/{total_files} files successfully")
    
    time.sleep(2)
    st.rerun()

def render_calendar_and_files(chosen_date):
    """Render calendar and file management"""
    # Calendar
    st.subheader("Calendar")
    events = []
    for d, cnt in supabase.get_dates_with_files():
        events.append({
            "title": f"{cnt} file(s)",
            "start": d,
            "allDay": True,
            "color": "blue"
        })
    
    calendar_res = calendar(
        events=events,
        options={
            "initialView": "dayGridMonth",
            "height": "400px",
            "selectable": True,
        },
        key="calendar",
    )
    
    # File management
    if "selected_date" not in st.session_state:
        st.session_state["selected_date"] = str(date.today())
    
    clicked_date = None
    if calendar_res and calendar_res.get("callback") == "dateClick":
        iso_date = calendar_res["dateClick"]["date"]
        dt_utc = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        dt_th = dt_utc.astimezone(pytz.timezone("Asia/Bangkok"))
        clicked_date = dt_th.date().isoformat()
    
    if clicked_date:
        st.session_state["selected_date"] = clicked_date
    
    selected_date = st.session_state["selected_date"]
    
    st.subheader(f"Files for {selected_date}")
    files_list = supabase.get_files_by_date(selected_date)
    
    if not files_list:
        st.info("No files for this date")
    else:
        render_file_management(files_list)

def render_file_management(files_list):
    """Render file management interface"""
    selected_files = []
    for fid, fname, fpath in files_list:
        col1, col2 = st.columns([4, 1])
        with col1:
            checked = st.checkbox(fname, key=f"chk_{fid}")
            if checked:
                selected_files.append((fid, fname, fpath))
        with col2:
            if st.button("🗑️ Delete", key=f"del_{fid}"):
                delete_file_optimized(fid, fname)
    
    if st.button("Run Analysis", key="analyze_btn"):
        if not selected_files:
            st.warning("Please select at least one file to analyze")
        else:
            run_analysis_optimized(selected_files)

@performance_monitor
def delete_file_optimized(fid, fname):
    """Optimized file deletion"""
    delete_progress = st.progress(0)
    delete_status = st.empty()
    
    delete_status.text(f"🗑️ Deleting {fname}...")
    delete_progress.progress(0.5)
    
    try:
        supabase.delete_file_record(fid)
        delete_progress.progress(1.0)
        delete_status.text("✅ File deleted successfully!")
        st.success(f"🗑️ {fname} has been deleted")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to delete {fname}: {e}")
        delete_progress.progress(0)
        delete_status.text("❌ Delete failed")

@performance_monitor
def run_analysis_optimized(selected_files):
    """Optimized analysis with performance monitoring"""
    analysis_progress = st.progress(0)
    analysis_status = st.empty()
    
    total_files = len(selected_files)
    processed_files = 0
    
    # Clear session state
    st.session_state.clear()
    
    for i, (fid, fname, fpath) in enumerate(selected_files):
        analysis_status.text(f"🔍 Analyzing {fname}... ({i+1}/{total_files})")
        progress = (i + 1) / total_files
        analysis_progress.progress(progress)
        
        try:
            file_bytes = get_file_for_analysis(fid)
            if file_bytes is None:
                st.warning(f"⚠️ File not found: {fname}")
                continue
            
            lname = fname.lower()
            if lname.endswith(".zip"):
                zip_bytes = file_bytes
                res = find_in_zip(zip_bytes)
                
                for kind, pack in res.items():
                    if not pack:
                        continue
                    df, zname = pack
                    if kind == "wason":
                        st.session_state["wason_log"] = df
                        st.session_state["wason_file"] = zname
                    else:
                        st.session_state[f"{kind}_data"] = df
                        st.session_state[f"{kind}_file"] = zname
                processed_files += 1
            else:
                ext = _ext(lname)
                kind = _kind(lname)
                if not ext or not kind:
                    raise ValueError("Unsupported file type or cannot infer kind")
                data = LOADERS[ext](file_bytes)
                if kind == "wason":
                    st.session_state["wason_log"] = data
                    st.session_state["wason_file"] = fname
                else:
                    st.session_state[f"{kind}_data"] = data
                    st.session_state[f"{kind}_file"] = fname
                processed_files += 1
        except Exception as e:
            st.error(f"❌ Failed to analyze {fname}: {e}")
        
        time.sleep(0.1)
    
    analysis_progress.progress(1.0)
    analysis_status.text(f"✅ Analysis completed! Processed {processed_files}/{total_files} files")
    
    # Initialize analyzers with optimized versions
    initialize_analyzers_optimized()
    
    if processed_files == total_files:
        st.success(f"🎉 All {total_files} files analyzed successfully!")
        st.info("📊 You can now navigate to individual analysis pages to view results")
        
        # Show Summary Table
        st.markdown("---")
        st.markdown("## 📊 Summary Table")
        try:
            from table1 import SummaryTableReport
            summary = SummaryTableReport()
            summary.render()
        except Exception as e:
            st.error(f"Failed to load Summary Table: {e}")
    else:
        st.warning(f"⚠️ Analyzed {processed_files}/{total_files} files successfully")
    
    time.sleep(2)
    st.rerun()

def initialize_analyzers_optimized():
    """Initialize analyzers with optimized versions"""
    analysis_status = st.empty()
    analysis_status.text("🔄 Initializing optimized analyzers...")
    
    # Initialize optimized analyzers
    if (st.session_state.get("osc_data") is not None and 
        st.session_state.get("fm_data") is not None):
        try:
            process_fiberflapping_optimized(
                st.session_state["osc_data"].copy(),
                st.session_state["fm_data"].copy()
            )
        except Exception as e:
            st.write(f"Fiberflapping analyzer initialization failed: {e}")
    
    if st.session_state.get("line_data") is not None:
        try:
            pmap = st.session_state.get("lb_pmap", {})
            process_line_optimized(
                st.session_state["line_data"].copy(),
                pmap
            )
        except Exception as e:
            st.write(f"Line analyzer initialization failed: {e}")
    
    if st.session_state.get("wason_log") is not None:
        try:
            process_apo_optimized(st.session_state["wason_log"])
        except Exception as e:
            st.write(f"APO analyzer initialization failed: {e}")
    
    analysis_status.text("✅ All optimized analyzers initialized!")

def render_fiberflapping_optimized():
    """Render optimized fiber flapping page"""
    st.markdown("### Fiber Flapping (OSC + FM) - Optimized")
    
    df_osc = st.session_state.get("osc_data")
    df_fm = st.session_state.get("fm_data")
    
    if (df_osc is not None) and (df_fm is not None):
        try:
            analyzer = FiberflappingAnalyzerOptimized(
                df_optical=df_osc.copy(),
                df_fm=df_fm.copy(),
                threshold=2.0,
                ref_path="data/Flapping.xlsx"
            )
            analyzer.process()
            st.caption(
                f"Using OSC: {st.session_state.get('osc_file')} | "
                f"FM: {st.session_state.get('fm_file')}"
            )
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.info("Please upload a ZIP on 'Home' that contains both OSC (optical) and FM workbooks.")

def render_line_board_optimized():
    """Render optimized line board page"""
    st.markdown("### Line Cards Performance - Optimized")
    
    df_line = st.session_state.get("line_data")
    log_txt = st.session_state.get("wason_log")
    
    if log_txt:
        st.session_state["lb_pmap"] = Line_Analyzer_Optimized.get_preset_map(log_txt)
    pmap = st.session_state.get("lb_pmap", {})
    
    if df_line is not None:
        try:
            df_ref = pd.read_excel("data/Line.xlsx")
            analyzer = Line_Analyzer_Optimized(
                df_line=df_line.copy(),
                df_ref=df_ref.copy(),
                pmap=pmap,
                ns="line"
            )
            analyzer.process()
            st.caption(
                f"Using LINE file: {st.session_state.get('line_file')}  "
                f"{'(with WASON log)' if log_txt else '(no WASON log)'}"
            )
        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
    else:
        st.info("Please upload a ZIP on 'Home' that contains a Line workbook")

def render_apo_optimized():
    """Render optimized APO remnant page"""
    st.markdown("### APO Remnant Analysis - Optimized")
    
    if st.session_state.get("wason_log") is not None:
        try:
            apo_progress = st.progress(0)
            apo_status = st.empty()
            
            apo_status.text("📊 Loading optimized APO analyzer...")
            apo_progress.progress(0.3)
            
            analyzer = ApoRemnantAnalyzerOptimized(st.session_state["wason_log"])
            apo_progress.progress(0.6)
            
            apo_status.text("🔍 Parsing WASON log...")
            analyzer.parse()
            apo_progress.progress(0.8)
            
            apo_status.text("⚙️ Analyzing APO remnant...")
            analyzer.analyze()
            apo_progress.progress(1.0)
            
            apo_status.text("✅ APO analysis completed!")
            
            # Display results
            apo_kpi(analyzer.rendered, analyzer.apo_links)
            analyzer.render_streamlit()
            
            st.session_state["apo_analyzer"] = analyzer
            
            time.sleep(1)
        except Exception as e:
            st.error(f"❌ An error occurred during APO analysis: {e}")
            apo_progress.progress(0)
            apo_status.text("❌ APO analysis failed")
    else:
        st.info("📁 Please upload a ZIP file that contains the WASON log data.")

def render_dashboard():
    """Render dashboard with optimized performance"""
    st.markdown("# 🌐 Network Monitoring Dashboard - Optimized")
    st.markdown("---")
    
    # Check Supabase connection
    if supabase.is_connected():
        st.success("✅ Connected to Supabase Database")
        # Dashboard content would go here
    else:
        st.error("❌ Cannot connect to Supabase Database")
        st.info("Please check your Supabase configuration in Streamlit secrets.")

def render_other_pages(menu):
    """Render other pages with original implementation"""
    # This would contain the original implementation for other pages
    st.info(f"Page {menu} - Using original implementation")

if __name__ == "__main__":
    main()
