import streamlit as st
import pandas as pd
from typing import Optional
from report import generate_report


from FAN_Analyzer import FAN_Analyzer
from CPU_Analyzer import CPU_Analyzer
from MSU_Analyzer import MSU_Analyzer
from Line_Analyzer import Line_Analyzer
from Client_Analyzer import Client_Analyzer
from Fiberflapping_Analyzer import FiberflappingAnalyzer
from EOL_Core_Analyzer import EOLAnalyzer, CoreAnalyzer
from Preset_Analyzer import PresetStatusAnalyzer
from APO_Analyzer import ApoRemnantAnalyzer

# ==============================
# Helper: auto-create analyzer
# ==============================
def _ensure_analyzer(key: str, analyzer_cls, ref_file: str, ns: str):
    """
    ตรวจสอบและสร้าง analyzer อัตโนมัติถ้ายังไม่มี
    key = 'cpu' หรือ 'fan' หรือ 'msu' หรือ 'line' หรือ 'client' หรือ 'eol' หรือ 'core'
    """
    analyzer_key = f"{key}_analyzer"
    data_key = f"{key}_data"

    if st.session_state.get(analyzer_key) is None and st.session_state.get(data_key) is not None:
        try:
            df_ref = pd.read_excel(ref_file)

            if key == "cpu":
                analyzer = analyzer_cls(
                    df_cpu=st.session_state[data_key].copy(),
                    df_ref=df_ref.copy(),
                    ns=ns
                )
            elif key == "fan":
                analyzer = analyzer_cls(
                    df_fan=st.session_state[data_key].copy(),
                    df_ref=df_ref.copy(),
                    ns=ns
                )
            elif key == "msu":
                analyzer = analyzer_cls(
                    df_msu=st.session_state[data_key].copy(),
                    df_ref=df_ref.copy(),
                    ns=ns
                )
            elif key == "line":
                analyzer = analyzer_cls(
                    df_line=st.session_state[data_key].copy(),
                    df_ref=df_ref.copy(),
                    ns=ns
                )
            elif key == "client":
                analyzer = analyzer_cls(
                    df_client=st.session_state[data_key].copy(),
                    ref_path=ref_file
                )
            elif key == "fiberflapping":
                # FiberflappingAnalyzer ต้องการ df_optical และ df_fm
                df_optical = st.session_state.get("osc_data")
                df_fm = st.session_state.get("fm_data")
                if df_optical is not None and df_fm is not None:
                    analyzer = analyzer_cls(
                        df_optical=df_optical.copy(),
                        df_fm=df_fm.copy(),
                        threshold=2.0,
                        ref_path=ref_file
                    )
                else:
                    return
            elif key == "eol":
                # EOLAnalyzer ต้องการ df_raw_data และ df_ref
                df_raw_data = st.session_state.get("atten_data")
                if df_raw_data is not None:
                    analyzer = analyzer_cls(
                        df_ref=None,
                        df_raw_data=df_raw_data.copy(),
                        ref_path=ref_file
                    )
                else:
                    return
            elif key == "core":
                # CoreAnalyzer ต้องการ df_raw_data และ df_ref
                df_raw_data = st.session_state.get("atten_data")  # Core ใช้ข้อมูลเดียวกับ EOL
                if df_raw_data is not None:
                    analyzer = analyzer_cls(
                        df_ref=None,
                        df_raw_data=df_raw_data.copy(),
                        ref_path=ref_file
                    )
                else:
                    return
            else:
                return

            analyzer.prepare()  # ✅ ใช้ prepare() (ไม่ render UI)
            st.session_state[analyzer_key] = analyzer

            pass
        except Exception as e:
            st.warning(f"Auto-create {key.upper()} analyzer failed: {e}")



# ==============================
# Styler Helper
# ==============================
#def _style_abnormal_table(df_abn: pd.DataFrame, value_col: str) -> "pd.io.formats.style.Styler":
    #"""ไฮไลต์ abnormal column (df_abn เป็น abnormal rows อยู่แล้ว)"""
    #def highlight_red(_):
        #return "background-color:#ff9999; color:black"
    #return df_abn.style.applymap(highlight_red, subset=[value_col])


def _ensure_preset_analyzer():
    """สร้าง Preset analyzer ถ้ายังไม่มี"""
    if (st.session_state.get("preset_analyzer") is None and 
        st.session_state.get("wason_log") is not None):
        try:
            analyzer = PresetStatusAnalyzer(st.session_state["wason_log"])
            analyzer.parse()
            analyzer.analyze()
            st.session_state["preset_analyzer"] = analyzer
        except Exception as e:
            st.warning(f"Failed to create preset analyzer: {e}")

def _ensure_apo_analyzer():
    """สร้าง APO analyzer ถ้ายังไม่มี"""
    if (st.session_state.get("apo_analyzer") is None and 
        st.session_state.get("wason_log") is not None):
        try:
            analyzer = ApoRemnantAnalyzer(st.session_state["wason_log"])
            analyzer.parse()
            analyzer.analyze()
            st.session_state["apo_analyzer"] = analyzer
        except Exception as e:
            st.warning(f"Failed to create APO analyzer: {e}")

# ==============================
# SummaryTableReport (รวมทุก Analyzer)
# ==============================
class SummaryTableReport:
    """Summary Table & Report รวมทุก Analyzer"""

    def __init__(self):
        self.sections = []  # เก็บ summary ของแต่ละ analyzer

    def _get_summary(self, key: str, analyzer_cls, details: str, value_col: str):
        """ดึง analyzer จาก session และคืนค่า (status, details, df_abn, df_abn_by_type)"""
        analyzer = st.session_state.get(f"{key}_analyzer")

        if analyzer is None:
            if key == "fiberflapping":
                # เพิ่มข้อความช่วยเหลือสำหรับ Fiber Flapping
                osc_data = st.session_state.get("osc_data")
                fm_data = st.session_state.get("fm_data")
                if osc_data is None and fm_data is None:
                    return ("No data", "Missing OSC and FM data files", None, {})
                elif osc_data is None:
                    return ("No data", "Missing OSC (Optical) data file", None, {})
                elif fm_data is None:
                    return ("No data", "Missing FM (Alarm) data file", None, {})
            return ("No data", details, None, {})

        # ดึง df_abnormal
        df_abn = getattr(analyzer, "df_abnormal", None)
        if df_abn is None:
            df_abn = pd.DataFrame()
        
        # ดึง df_abnormal_by_type
        df_abn_by_type = getattr(analyzer, "df_abnormal_by_type", {})
        
        # กำหนด status
        status = "Normal"
        if not df_abn.empty:
            status = "Abnormal"
        elif df_abn is None or (isinstance(df_abn, pd.DataFrame) and df_abn.empty):
            # ตรวจสอบใน df_abnormal_by_type ด้วย
            has_abn = False
            if df_abn_by_type:
                for subtype, subdf in df_abn_by_type.items():
                    if isinstance(subdf, pd.DataFrame) and not subdf.empty:
                        has_abn = True
                        break
            status = "Abnormal" if has_abn else "Normal"

        return (status, details, df_abn, df_abn_by_type)

    def _get_preset_summary(self):
        """ดึงข้อมูล Preset summary"""
        analyzer = st.session_state.get("preset_analyzer")
        if analyzer is None:
            return ("No data", "Preset usage analysis from WASON logs", None, {})
        
        try:
            df, summary = analyzer.to_dataframe()
            
            if df is not None and not df.empty:
                # กำหนด abnormal โดยอิง Verdict ถ้ามี ไม่เช่นนั้น fallback ที่ Status != "Normal"
                df_abnormal = df.copy()
                if "Verdict" in df_abnormal.columns:
                    df_abnormal = df_abnormal[df_abnormal["Verdict"] == "FAIL"]
                elif "Status" in df_abnormal.columns:
                    df_abnormal = df_abnormal[df_abnormal["Status"] != "Normal"]
                
                # เลือกเฉพาะคอลัมน์ที่ต้องการแสดง (ไม่เอา Raw)
                cols_to_show = ["Call", "IP", "Preroute", "Verdict", "Status"]
                df_abnormal = df_abnormal[[c for c in cols_to_show if c in df_abnormal.columns]]
                
                # ตรวจสอบว่ามี abnormal presets หรือไม่
                if not df_abnormal.empty:
                    return ("Abnormal", "Preset usage analysis from WASON logs", df_abnormal, {"Preset": df_abnormal})
                else:
                    return ("Normal", "Preset usage analysis from WASON logs", None, {})
            else:
                return ("No data", "Preset usage analysis from WASON logs", None, {})
        except Exception as e:
            st.warning(f"Preset summary error: {e}")
            import traceback
            st.code(traceback.format_exc())
            return ("Error", "Preset usage analysis from WASON logs", None, {})

    def _get_apo_summary(self):
        """ดึงข้อมูล APO summary พร้อมรายละเอียด links"""
        analyzer = st.session_state.get("apo_analyzer")
        if analyzer is None:
            return ("No data", "APO remnant analysis from WASON logs", None, {})
        
        try:
            rendered = getattr(analyzer, "rendered", [])
            site_map = getattr(analyzer, "site_map", {})
            
            if rendered:
                # ตรวจสอบว่ามี APO remnants หรือไม่
                apo_count = sum(1 for x in rendered if len(x) >= 3 and x[2])
                
                if apo_count > 0:
                    # สร้าง detailed summary text
                    apo_details = []
                    
                    # Group by site
                    for item in rendered:
                        if len(item) >= 4:
                            wip = item[0]
                            dest_tuple = item[1]  # (site_name, wason_snippet, apop_snippet, to_red_wason, to_red_apop)
                            has_apo = item[2]
                            
                            if has_apo:
                                site_name = dest_tuple[0] if len(dest_tuple) > 0 else wip
                                
                                # ดึง APOP lines ที่มี remnant (ตัวที่เป็นสีแดง)
                                apop_snippet = dest_tuple[2] if len(dest_tuple) > 2 else ""
                                to_red_apop = dest_tuple[4] if len(dest_tuple) > 4 else set()
                                
                                # เพิ่มหัวข้อ Site
                                apo_details.append(f"\n**Site: {site_name} ({wip})**\n")
                                
                                # แสดง remnant lines
                                if apop_snippet:
                                    apop_lines = apop_snippet.split('\n')
                                    
                                    # หา header line
                                    header_line = None
                                    for line in apop_lines:
                                        if '[APOPLUS]No' in line and 'SourceNodeID' in line:
                                            header_line = line
                                            break
                                    
                                    # Group remnants by source→destination
                                    remnant_by_link = {}
                                    for line in apop_lines:
                                        if line in to_red_apop and '[APOPLUS]' in line:
                                            # Parse line to get source and dest hex
                                            parts = line.split()
                                            if len(parts) >= 3:
                                                try:
                                                    src_hex = parts[1]
                                                    dst_hex = parts[2]
                                                    
                                                    # Convert hex to IP
                                                    src_ip = analyzer._hex_to_ip(src_hex)
                                                    dst_ip = analyzer._hex_to_ip(dst_hex)
                                                    src_name = site_map.get(src_ip, src_ip)
                                                    dst_name = site_map.get(dst_ip, dst_ip)
                                                    
                                                    link_key = f"{src_name} ({src_ip}) → {dst_name} ({dst_ip})"
                                                    
                                                    if link_key not in remnant_by_link:
                                                        remnant_by_link[link_key] = []
                                                    remnant_by_link[link_key].append(line)
                                                except:
                                                    pass
                                    
                                    # แสดงแต่ละ link
                                    for link_key, lines in sorted(remnant_by_link.items()):
                                        apo_details.append(f"   **{link_key}**")
                                        apo_details.append("```")
                                        if header_line:
                                            apo_details.append(header_line)
                                        for line in lines:
                                            apo_details.append(line)
                                        apo_details.append("```")
                                        apo_details.append("")  # blank line
                    
                    # Join all details
                    apo_summary_text = "\n".join(apo_details)
                    
                    return ("Abnormal", "APO remnant analysis from WASON logs", apo_summary_text, {"APO": apo_summary_text})
                else:
                    return ("Normal", "APO remnant analysis from WASON logs", None, {})
            else:
                return ("No data", "APO remnant analysis from WASON logs", None, {})
        except Exception as e:
            st.warning(f"APO summary error: {e}")
            import traceback
            st.code(traceback.format_exc())
            return ("Error", "APO remnant analysis from WASON logs", None, {})

    def render(self) -> None:
        st.markdown("## Summary Table — Network Inspection")

        #2 ✅ Ensure analyzers are ready
        with st.spinner("🔄 Initializing analyzers..."):
            _ensure_analyzer("cpu", CPU_Analyzer, "data/CPU.xlsx", "cpu_summary")
            _ensure_analyzer("fan", FAN_Analyzer, "data/FAN.xlsx", "fan_summary")
            _ensure_analyzer("msu", MSU_Analyzer, "data/MSU.xlsx", "msu_summary")
            _ensure_analyzer("line", Line_Analyzer, "data/Line.xlsx", "line_summary")
            _ensure_analyzer("client", Client_Analyzer, "data/Client.xlsx", "client_summary")
            _ensure_analyzer("fiberflapping", FiberflappingAnalyzer, "data/Flapping.xlsx", "fiberflapping_summary")
            _ensure_analyzer("eol", EOLAnalyzer, "data/EOL.xlsx", "eol_summary")
            _ensure_analyzer("core", CoreAnalyzer, "data/EOL.xlsx", "core_summary")
            
            # เพิ่ม Preset และ APO analyzers
            _ensure_preset_analyzer()
            _ensure_apo_analyzer()
        
   






        # ===== Header =====
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 1, 1])
        col1.markdown("### Type")
        col2.markdown("### Task")
        col3.markdown("### Details")
        col4.markdown("### Results")
        col5.markdown("### View")
        st.markdown("---")

        # ==============================
        # CPU Section
        # ==============================
        #3
        CPU_DETAILS = "Threshold: Normal if ≤ 90%, Abnormal if > 90%"
        cpu_status, cpu_details, cpu_abn, cpu_abn_by_type = self._get_summary(
            "cpu", CPU_Analyzer, CPU_DETAILS, "CPU utilization ratio"
        )
        self._render_row("Performance", "Control board", cpu_details, cpu_status, cpu_abn, "CPU utilization ratio")

        # ==============================
        # FAN Section
        # ==============================
        FAN_DETAILS = (
            "FAN ratio performance\n"
            "FCC: Normal if ≤ 120, Abnormal if > 120\n"
            "FCPP: Normal if ≤ 250, Abnormal if > 250\n"
            "FCPL: Normal if ≤ 120, Abnormal if > 120\n"
            "FCPS: Normal if ≤ 230, Abnormal if > 230"
        )
        fan_status, fan_details, fan_abn, fan_abn_by_type = self._get_summary(
            "fan", FAN_Analyzer, FAN_DETAILS, "Value of Fan Rotate Speed(Rps)"
        )
        self._render_row("Performance", "FAN board", fan_details, fan_status, fan_abn, "Value of Fan Rotate Speed(Rps)")

        # ==============================
        # MSU Section
        # ==============================
        MSU_DETAILS = "Threshold: Should remain within normal range (not high)"
        msu_status, msu_details, msu_abn, msu_abn_by_type = self._get_summary(
            "msu", MSU_Analyzer, MSU_DETAILS, "Laser Bias Current(mA)"
        )
        self._render_row("Performance", "MSU board", msu_details, msu_status, msu_abn, "Laser Bias Current(mA)")

        # ==============================
        # LINE Section
        # ==============================
        LINE_DETAILS = "Normal input/output power [xx–xx dB]"
        line_status, line_details, line_abn, line_abn_by_type = self._get_summary(
            "line", Line_Analyzer, LINE_DETAILS, "Instant BER After FEC"
        )
        self._render_row("Performance", "Line board", line_details, line_status, line_abn, "Instant BER After FEC")

        CLIENT_DETAILS = ("Normal input/output power [xx–xx dB]")
        client_status, client_details, client_abn, client_abn_by_type = self._get_summary(
            "client", Client_Analyzer, CLIENT_DETAILS, "Input Optical Power(dBm)"
        )
        self._render_row("Performance", "Client board", client_details, client_status, client_abn, "Input Optical Power(dBm)")

        # ==============================
        # FLAPPING Section
        # ==============================
        FLAP_DETAILS = "Threshold: Normal if ≤ 2 dB, Abnormal if > 2 dB"
        fiber_status, fiber_details, fiber_abn, fiber_abn_by_type = self._get_summary(
            "fiberflapping", FiberflappingAnalyzer, FLAP_DETAILS, "Max - Min (dB)"
        )
        self._render_row("Performance", "Fiber Flapping", fiber_details, fiber_status, fiber_abn, "Max - Min (dB)")

        # ==============================
        # EOL Section
        # ==============================
        EOL_DETAILS = "Threshold: Normal if ≤ 2.5 dB, Abnormal if > 2.5 dB"
        eol_status, eol_details, eol_abn, eol_abn_by_type = self._get_summary(
            "eol", EOLAnalyzer, EOL_DETAILS, "Loss current - Loss EOL"
        )
        self._render_row("Performance", "Loss between EOL", eol_details, eol_status, eol_abn, "Loss current - Loss EOL")

        # ==============================
        # CORE Section
        # ==============================
        CORE_DETAILS = "Threshold: Normal if ≤ 3 dB, Abnormal if > 3 dB"
        core_status, core_details, core_abn, core_abn_by_type = self._get_summary(
            "core", CoreAnalyzer, CORE_DETAILS, "Loss between core"
        )
        self._render_row("Performance", "Loss between core", core_details, core_status, core_abn, "Loss between core")

        # ==============================
        # PRESET Section
        # ==============================
        PRESET_DETAILS = "Preset usage analysis from WASON logs"
        preset_status, preset_details, preset_abn, preset_abn_by_type = self._get_preset_summary()
        self._render_row("Configuration", "Preset status", preset_details, preset_status, preset_abn, "Preset")

        # ==============================
        # APO Section
        # ==============================
        APO_DETAILS = "APO remnant analysis from WASON logs"
        apo_status, apo_details, apo_abn, apo_abn_by_type = self._get_apo_summary()
        self._render_row("Configuration", "APO remnant", apo_details, apo_status, apo_abn, "APO")


        #4 ===== Export PDF รวม =====
        st.markdown("---")
        st.markdown("### 📊 Export Comprehensive Report")
        st.markdown("Generate a detailed PDF report containing all analysis results and abnormal data.")
        all_abnormal = {
            "CPU": cpu_abn_by_type,   # ✅ CPU มาก่อน
            "FAN": fan_abn_by_type,
            "MSU": msu_abn_by_type,
            "Line": line_abn_by_type,
            "Client": client_abn_by_type,
            "Fiber": fiber_abn_by_type,
            "EOL": eol_abn_by_type,
            "Core": core_abn_by_type,
            "Preset": preset_abn_by_type,
            "APO": apo_abn_by_type
        }
        
        # สร้างปุ่ม Generate Report พร้อม Progress bar (ชิดซ้าย)
        if st.button("📊 Generate PDF Report", key="generate_report_btn", use_container_width=True):
                # สร้าง Progress bar
                report_progress = st.progress(0)
                report_status = st.empty()
                
                try:
                    # Step 1: Collecting data
                    report_status.text("📋 Collecting analysis data...")
                    report_progress.progress(0.2)
                    import time
                    time.sleep(0.5)
                    
                    # Step 2: Generating PDF
                    report_status.text("📄 Generating PDF report...")
                    report_progress.progress(0.6)
                    pdf_bytes = generate_report(all_abnormal=all_abnormal)
                    
                    # Step 3: Finalizing
                    report_status.text("✅ Report generation completed!")
                    report_progress.progress(1.0)
                    time.sleep(0.5)
                    
                    # แสดงปุ่มดาวน์โหลด
                    st.success("🎉 PDF Report generated successfully!")
                    st.download_button(
                        label="📥 Download Report (All Sections)",
                        data=pdf_bytes,
                        file_name=f"Network_Inspection_Report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        key="download_report_btn"
                    )
                    
                except Exception as e:
                    st.error(f"❌ Failed to generate report: {e}")
                    report_progress.progress(0)
                    report_status.text("❌ Report generation failed")
        else:
            # แสดงข้อความชิดซ้ายเมื่อยังไม่ได้กด Generate
            st.markdown("💡 Click 'Generate PDF Report' to create your comprehensive network inspection report")

    def _render_row(self, type_name, task_name, details, status, df_abn, value_col: str, df_abn_by_type=None):
        """วาด summary row + toggle abnormal"""
        col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 1, 1])
        
        # Type column without icon
        col1.markdown(f"**{type_name}**")
        
        # Task column
        col2.markdown(f"**{task_name}**")
        
        # Details column
        col3.markdown(details.replace("\n", "<br>"), unsafe_allow_html=True)

        # Result cell
        if status == "Abnormal":
            col4.markdown(
                "<div style='background-color:#FFECEC; color:#B00020; font-weight:bold; "
                "text-align:center; padding:4px; border-radius:4px;'>Abnormal</div>",
                unsafe_allow_html=True
            )
        elif status == "Normal":
            col4.markdown(
                "<div style='background-color:#E6FFEC; color:#0F7B3E; font-weight:bold; "
                "text-align:center; padding:4px; border-radius:4px;'>Normal</div>",
                unsafe_allow_html=True
            )
        else:
            col4.write(status)

        # ✅ ใช้ key แยกสำหรับ state กับปุ่ม
        key_state = f"{task_name}_show_table"
        key_button = f"{task_name}_toggle_btn"

        if key_state not in st.session_state:
            st.session_state[key_state] = False

        # View button with icon
        button_text = "Hide" if st.session_state[key_state] else "View"
        if col5.button(button_text, key=key_button):
            st.session_state[key_state] = not st.session_state[key_state]

        # Drilldown abnormal table
        if st.session_state[key_state]:
            if status == "Abnormal" and df_abn is not None:
                st.markdown(f"#### Abnormal {task_name} Table")


         

                # ===================== CPU =====================
                if task_name == "Control board":
                    cols_to_show = ["Site Name", "ME", "Measure Object",
                                    "Maximum threshold", "Minimum threshold", "CPU utilization ratio"]
                    df_abn = df_abn[cols_to_show].copy()

                    numeric_cols = [c for c in df_abn.columns if c not in ["Site Name", "ME", "Measure Object"]]
                    for c in numeric_cols:
                        df_abn[c] = pd.to_numeric(df_abn[c], errors="coerce")

                    def hl_cpu_row(row):
                        styles = [""] * len(row)
                        col_map = {c: i for i, c in enumerate(df_abn.columns)}
                        try:
                            cpu_val = float(row.get("CPU utilization ratio", 0))
                            if pd.notna(cpu_val) and cpu_val > 0:
                                cidx = col_map.get("CPU utilization ratio")
                                if cidx is not None:
                                    styles[cidx] = "background-color:#ff9999; color:black"
                        except (ValueError, TypeError):
                            pass
                        return styles

                    styled = (
                        df_abn.style
                        .format({c: "{:.2f}" for c in numeric_cols}, na_rep="-")
                        .apply(hl_cpu_row, axis=1)
                    )
                    st.dataframe(styled, use_container_width=True)

                # ===================== FAN =====================
                elif task_name == "FAN board":
                    cols_to_show = ["Site Name", "ME", "Measure Object",
                                    "Maximum threshold", "Minimum threshold", "Value of Fan Rotate Speed(Rps)"]
                    df_abn = df_abn[cols_to_show].copy()

                    numeric_cols = [c for c in df_abn.columns if c not in ["Site Name", "ME", "Measure Object"]]
                    for c in numeric_cols:
                        df_abn[c] = pd.to_numeric(df_abn[c], errors="coerce")

                    def hl_fan_row(row):
                        styles = [""] * len(row)
                        col_map = {c: i for i, c in enumerate(df_abn.columns)}
                        try:
                            fan_val = float(row.get("Value of Fan Rotate Speed(Rps)", 0))
                            if pd.notna(fan_val) and fan_val > 0:
                                cidx = col_map.get("Value of Fan Rotate Speed(Rps)")
                                if cidx is not None:
                                    styles[cidx] = "background-color:#ff9999; color:black"
                        except (ValueError, TypeError):
                            pass
                        return styles

                    styled = (
                        df_abn.style
                        .format({c: "{:.2f}" for c in numeric_cols}, na_rep="-")
                        .apply(hl_fan_row, axis=1)
                    )
                    st.dataframe(styled, use_container_width=True)

                # ===================== MSU =====================
                elif task_name == "MSU board":
                    cols_to_show = ["Site Name", "ME", "Measure Object",
                                    "Maximum threshold", "Laser Bias Current(mA)"]
                    df_abn = df_abn[cols_to_show].copy()

                    numeric_cols = [c for c in df_abn.columns if c not in ["Site Name", "ME", "Measure Object"]]
                    for c in numeric_cols:
                        df_abn[c] = pd.to_numeric(df_abn[c], errors="coerce")

                    def hl_msu_row(row):
                        styles = [""] * len(row)
                        col_map = {c: i for i, c in enumerate(df_abn.columns)}
                        try:
                            msu_val = float(row.get("Laser Bias Current(mA)", 0))
                            if pd.notna(msu_val) and msu_val > 0:
                                cidx = col_map.get("Laser Bias Current(mA)")
                                if cidx is not None:
                                    styles[cidx] = "background-color:#ff9999; color:black"
                        except (ValueError, TypeError):
                            pass
                        return styles

                    styled = (
                        df_abn.style
                        .format({c: "{:.2f}" for c in numeric_cols}, na_rep="-")
                        .apply(hl_msu_row, axis=1)
                    )
                    st.dataframe(styled, use_container_width=True)

                # ===================== LINE =====================
                elif task_name == "Line board":
                    # ใช้ข้อมูลจาก Line_Analyzer ที่เตรียมไว้แล้ว
                    line_analyzer = st.session_state.get("line_analyzer")
                    if line_analyzer and hasattr(line_analyzer, 'df_abnormal') and not line_analyzer.df_abnormal.empty:
                        df_abn = line_analyzer.df_abnormal.copy()
                        
                        # เลือกคอลัมน์ที่จำเป็น
                        cols_to_show = [
                            "Site Name", "ME", "Call ID", "Measure Object",
                            "Threshold", "Instant BER After FEC",
                            "Maximum threshold(out)", "Minimum threshold(out)", "Output Optical Power (dBm)",
                            "Maximum threshold(in)", "Minimum threshold(in)", "Input Optical Power(dBm)",
                            "Route"
                        ]
                        df_abn = df_abn[[c for c in cols_to_show if c in df_abn.columns]].copy()

                        # แปลงค่าเป็น numeric
                        numeric_cols = [c for c in df_abn.columns if c not in ["Site Name", "ME", "Measure Object", "Call ID", "Route"]]
                        for c in numeric_cols:
                            df_abn[c] = pd.to_numeric(df_abn[c], errors="coerce")

                        def highlight_line_row(row):
                            styles = [""] * len(row)
                            col_map = {c: i for i, c in enumerate(df_abn.columns)}

                            # BER check - ใช้เงื่อนไขเดียวกับ _render_abnormal_line_data()
                            try:
                                ber = float(row.get("Instant BER After FEC", 0))
                                thr = float(row.get("Threshold", 0))
                                if pd.notna(thr) and (pd.isna(ber) or ber > 0):
                                    styles[col_map["Instant BER After FEC"]] = "background-color:#ff4d4d; color:white"
                            except (ValueError, TypeError):
                                try:
                                    thr = float(row.get("Threshold", 0))
                                    if pd.notna(thr):
                                        styles[col_map["Instant BER After FEC"]] = "background-color:#ff4d4d; color:white"
                                except (ValueError, TypeError):
                                    pass

                            # Input check
                            try:
                                v = float(row.get("Input Optical Power(dBm)", 0))
                                lo = float(row.get("Minimum threshold(in)", 0))
                                hi = float(row.get("Maximum threshold(in)", 0))
                                if pd.notna(v) and pd.notna(lo) and pd.notna(hi) and (v < lo or v > hi):
                                    styles[col_map["Input Optical Power(dBm)"]] = "background-color:#ff4d4d; color:white"
                            except (ValueError, TypeError):
                                pass

                            # Output check
                            try:
                                v = float(row.get("Output Optical Power (dBm)", 0))
                                lo = float(row.get("Minimum threshold(out)", 0))
                                hi = float(row.get("Maximum threshold(out)", 0))
                                if pd.notna(v) and pd.notna(lo) and pd.notna(hi) and (v < lo or v > hi):
                                    styles[col_map["Output Optical Power (dBm)"]] = "background-color:#ff4d4d; color:white"
                            except (ValueError, TypeError):
                                pass

                            return styles

                        styled = (
                            df_abn.style
                            .apply(highlight_line_row, axis=1)
                            .format({
                                "Threshold": "{:.2E}",
                                "Instant BER After FEC": "{:.2E}",
                                "Input Optical Power(dBm)": "{:.4f}",
                                "Output Optical Power (dBm)": "{:.4f}",
                                "Minimum threshold(in)": "{:.4f}",
                                "Maximum threshold(in)": "{:.4f}",
                                "Minimum threshold(out)": "{:.4f}",
                                "Maximum threshold(out)": "{:.4f}"
                            }, na_rep="-")
                        )
                        st.dataframe(styled, use_container_width=True)
                    else:
                        st.info("No abnormal Line board data found.")

                # ===================== CLIENT =====================
                elif task_name == "Client board":
                    cols_to_show = [
                        "Site Name", "ME", "Measure Object",
                        "Maximum threshold(out)", "Minimum threshold(out)", "Output Optical Power (dBm)",
                        "Maximum threshold(in)", "Minimum threshold(in)", "Input Optical Power(dBm)"
                    ]
                    df_abn = df_abn[[c for c in cols_to_show if c in df_abn.columns]].copy()

                    def highlight_client_row(row):
                        styles = [""] * len(row)
                        col_map = {c: i for i, c in enumerate(df_abn.columns)}

                        try:
                            v, lo, hi = row["Output Optical Power (dBm)"], row["Minimum threshold(out)"], row["Maximum threshold(out)"]
                            if pd.notna(v) and pd.notna(lo) and pd.notna(hi) and (v < lo or v > hi):
                                styles[col_map["Output Optical Power (dBm)"]] = "background-color:#ff9999; color:black"
                        except:
                            pass

                        try:
                            v, lo, hi = row["Input Optical Power(dBm)"], row["Minimum threshold(in)"], row["Maximum threshold(in)"]
                            if pd.notna(v) and pd.notna(lo) and pd.notna(hi) and (v < lo or v > hi):
                                styles[col_map["Input Optical Power(dBm)"]] = "background-color:#ff9999; color:black"
                        except:
                            pass

                        return styles

                    styled = df_abn.style.apply(highlight_client_row, axis=1)
                    st.dataframe(styled, use_container_width=True)

                # ===================== FIBER FLAPPING =====================
                elif task_name == "Fiber Flapping":
                    if df_abn is not None and not df_abn.empty:
                        # แยกข้อมูลตามวัน
                        df_with_date = df_abn.copy()
                        df_with_date["Date"] = pd.to_datetime(df_with_date["Begin Time"]).dt.date
                        
                        # เรียงตามวัน (เก่า -> ใหม่)
                        dates_sorted = sorted(df_with_date["Date"].unique())
                        
                        cols_to_show = [
                            "Begin Time", "End Time", "Site Name", "ME", "Measure Object",
                            "Max Value of Input Optical Power(dBm)",
                            "Min Value of Input Optical Power(dBm)",
                            "Max - Min (dB)"
                        ]
                        
                        # แสดงข้อมูลแต่ละวัน
                        for date in dates_sorted:
                            df_day = df_with_date[df_with_date["Date"] == date].copy()
                            num_sites = df_day["ME"].nunique() if "ME" in df_day.columns else len(df_day)
                            
                            # สรุปจำนวน flapping ต่อ Site Name เรียงจากมากไปน้อย
                            site_counts_str = ""
                            if not df_day.empty and "Site Name" in df_day.columns:
                                counts = df_day["Site Name"].value_counts().reset_index()
                                counts.columns = ["Site Name", "Count"]
                                
                                # สร้างข้อความรวมในบรรทัดเดียว เช่น Jasmine_Z-E33 (3 links)
                                site_counts_str = " ".join([
                                    f"{r['Site Name']} ({r['Count']} link{'s' if r['Count'] > 1 else ''})"
                                    for _, r in counts.iterrows()
                                ])
                            
                            # หัวข้อวัน + รายชื่อไซต์
                            st.markdown(f"**{date} ({num_sites} sites)** {site_counts_str}")
                            
                            # เลือกคอลัมน์ที่จะแสดง
                            df_show = df_day[[c for c in cols_to_show if c in df_day.columns]].copy()
                            
                            # แปลงคอลัมน์ตัวเลขเป็น numeric
                            numeric_cols = [
                                "Max Value of Input Optical Power(dBm)",
                                "Min Value of Input Optical Power(dBm)",
                                "Max - Min (dB)"
                            ]
                            for col in numeric_cols:
                                if col in df_show.columns:
                                    df_show[col] = pd.to_numeric(df_show[col], errors="coerce")
                            
                            # ✅ Highlight Max - Min (dB) > 2.0 - ใช้ apply แบบใหม่
                            def hl_flapping_row(row):
                                styles = [""] * len(row)
                                col_map = {c: i for i, c in enumerate(df_show.columns)}
                                
                                try:
                                    # ใช้ row.get() เหมือนส่วนอื่นๆ
                                    max_min_val = float(row.get("Max - Min (dB)", 0))
                                    if pd.notna(max_min_val) and max_min_val > 2.0:
                                        cidx = col_map.get("Max - Min (dB)")
                                        if cidx is not None:
                                            styles[cidx] = "background-color:#ff4d4d; color:white"
                                except (ValueError, TypeError):
                                    pass
                                
                                return styles
                            
                            # Format ทศนิยม 2 ตำแหน่ง
                            format_dict = {col: "{:.2f}" for col in numeric_cols if col in df_show.columns}
                            
                            # ✅ ใช้ apply แทน applymap (รองรับ pandas >=2.1.0)
                            styled = (
                                df_show.style
                                .apply(hl_flapping_row, axis=1)
                                .format(format_dict, na_rep="-")
                            )
                            st.dataframe(styled, use_container_width=True, height=min(len(df_show) * 35 + 38, 400))
                            
                            # เว้นบรรทัดระหว่างวัน
                            st.markdown("")
                    else:
                        st.info("No abnormal fiber flapping data to display")

                # ===================== EOL =====================
                elif task_name == "Loss between EOL":
                    # EOL มี 2 ประเภท: Excess Loss และ Fiber Break
                    analyzer = st.session_state.get("eol_analyzer")
                    if analyzer and hasattr(analyzer, "abnormal_tables"):
                        abn_tables = analyzer.abnormal_tables
                        
                        # EOL Excess Loss
                        if "EOL Excess Loss" in abn_tables and not abn_tables["EOL Excess Loss"].empty:
                            st.markdown("**EOL Excess Loss**")
                            df_excess = abn_tables["EOL Excess Loss"]
                            
                            def hl_loss_row(row):
                                styles = [""] * len(row)
                                col_map = {c: i for i, c in enumerate(df_excess.columns)}
                                cidx = col_map.get("Loss current - Loss EOL")
                                if cidx is not None:
                                    styles[cidx] = "background-color: #ffe6e6"
                                return styles
                            
                            styled = df_excess.style.apply(hl_loss_row, axis=1)
                            st.dataframe(styled, use_container_width=True)
                        
                        # EOL Fiber Break
                        if "EOL Fiber Break" in abn_tables and not abn_tables["EOL Fiber Break"].empty:
                            st.markdown("**EOL Fiber Break**")
                            df_break = abn_tables["EOL Fiber Break"]
                            
                            def hl_remark_row(row):
                                styles = [""] * len(row)
                                col_map = {c: i for i, c in enumerate(df_break.columns)}
                                cidx = col_map.get("Remark")
                                if cidx is not None:
                                    remark_val = str(row.get("Remark", ""))
                                    if remark_val.strip() != "":
                                        styles[cidx] = "background-color: #fff8cc"
                                return styles
                            
                            styled = df_break.style.apply(hl_remark_row, axis=1)
                            st.dataframe(styled, use_container_width=True)
                        
                        if all(abn_tables[k].empty for k in ["EOL Excess Loss", "EOL Fiber Break"] if k in abn_tables):
                            st.info("No abnormal EOL data to display")
                    else:
                        st.info("No abnormal EOL data to display")

                # ===================== CORE =====================
                elif task_name == "Loss between core":
                    # Core มี 2 ประเภท: Loss Excess และ Fiber Break
                    analyzer = st.session_state.get("core_analyzer")
                    if analyzer and hasattr(analyzer, "abnormal_tables"):
                        abn_tables = analyzer.abnormal_tables
                        
                        # Core Loss Excess
                        if "Core Loss Excess" in abn_tables and not abn_tables["Core Loss Excess"].empty:
                            st.markdown("**Core Loss Excess**")
                            df_loss = abn_tables["Core Loss Excess"]
                            
                            def hl_red_row(row):
                                styles = [""] * len(row)
                                col_map = {c: i for i, c in enumerate(df_loss.columns)}
                                cidx = col_map.get("Loss between core")
                                if cidx is not None:
                                    styles[cidx] = "background-color: #ffe6e6"
                                return styles
                            
                            styled = df_loss.style.apply(hl_red_row, axis=1)
                            st.dataframe(styled, use_container_width=True)
                        
                        # Core Fiber Break
                        if "Core Fiber Break" in abn_tables and not abn_tables["Core Fiber Break"].empty:
                            st.markdown("**Core Fiber Break**")
                            df_break = abn_tables["Core Fiber Break"]
                            
                            def hl_yellow_row(row):
                                styles = [""] * len(row)
                                col_map = {c: i for i, c in enumerate(df_break.columns)}
                                cidx = col_map.get("Loss between core")
                                if cidx is not None:
                                    styles[cidx] = "background-color: #fff8cc"
                                return styles
                            
                            styled = df_break.style.apply(hl_yellow_row, axis=1)
                            st.dataframe(styled, use_container_width=True)
                        
                        if all(abn_tables[k].empty for k in ["Core Loss Excess", "Core Fiber Break"] if k in abn_tables):
                            st.info("No abnormal Core data to display")
                    else:
                        st.info("No abnormal Core data to display")

                # ===================== PRESET =====================
                elif task_name == "Preset status":
                    if df_abn is not None and not df_abn.empty:
                        st.dataframe(df_abn, use_container_width=True)
                    else:
                        st.info("No abnormal preset data to display")

                # ===================== APO =====================
                elif task_name == "APO remnant":
                    if df_abn is not None and isinstance(df_abn, str):
                        # df_abn เป็น text summary ของ APO remnants
                        st.markdown(df_abn)
                    elif df_abn is not None:
                        st.dataframe(df_abn, use_container_width=True)
                    else:
                        st.info("No APO remnant data to display")

            elif status == "Normal":
                st.info(f"✅ All {task_name} normal ")
            else:
                st.warning(f"⚠️ No {task_name} data available.")
        
        # Add separator between rows
        st.markdown("---")
