from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

import io
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def _df_to_wrapped_table(df: pd.DataFrame, style: ParagraphStyle) -> list[list]:
    """Convert a DataFrame to a table data matrix using Paragraph cells to allow word wrapping."""
    headers = [Paragraph(str(c), style) for c in df.columns]
    rows = []
    for _, r in df.iterrows():
        row = [Paragraph(str(r[c]) if pd.notna(r[c]) else "", style) for c in df.columns]
        rows.append(row)
    return [headers] + rows

def _colored(text: str, color: str, base_style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"<font color='{color}'>{text}</font>", base_style)

def _has_abnormal(abn_dict: dict) -> bool:
    if not abn_dict:
        return False
    for _sub, data in abn_dict.items():
        # รองรับทั้ง DataFrame และ String (สำหรับ APO)
        if isinstance(data, pd.DataFrame) and not data.empty:
            return True
        elif isinstance(data, str) and data.strip():
            return True
    return False

def _build_summary_rows(all_abnormal: dict) -> list[tuple[str, str, str, str]]:
    """Build summary rows: (Type, Task, Details, Result)."""
    details_map = {
        "CPU": "Threshold: Normal if ≤ 90%, Abnormal if > 90%",
        "FAN": (
            "FAN ratio performance\n"
            "FCC: Normal if ≤ 120, Abnormal if > 120\n"
            "FCPP: Normal if ≤ 250, Abnormal if > 250\n"
            "FCPL: Normal if ≤ 120, Abnormal if > 120\n"
            "FCPS: Normal if ≤ 230, Abnormal if > 230"
        ),
        "MSU": "Threshold: Should remain within normal range (not high)",
        "Line": "Normal input/output power [xx–xx dB]",
        "Client": "Normal input/output power [xx–xx dB]",
        "Fiber": "Threshold: Normal if ≤ 2 dB, Abnormal if > 2 dB",
        "EOL": "Threshold: Normal if ≤ 2.5 dB, Abnormal if > 2.5 dB",
        "Core": "Threshold: Normal if ≤ 3 dB, Abnormal if > 3 dB",
        "Preset": "Preset usage analysis from WASON logs",
        "APO": "APO remnant analysis from WASON logs",
    }
    task_map = {
        "CPU": "Control board",
        "FAN": "FAN board",
        "MSU": "MSU board",
        "Line": "Line board",
        "Client": "Client board",
        "Fiber": "Fiber Flapping",
        "EOL": "Loss between EOL",
        "Core": "Loss between core",
        "Preset": "Preset status",
        "APO": "APO remnant",
    }
    type_map = {
        "CPU": "Performance",
        "FAN": "Performance",
        "MSU": "Performance",
        "Line": "Performance",
        "Client": "Performance",
        "Fiber": "Performance",
        "EOL": "Performance",
        "Core": "Performance",
        "Preset": "Configuration",
        "APO": "Configuration",
    }

    rows: list[tuple[str, str, str, str]] = []
    for key in ["CPU", "FAN", "MSU", "Line", "Client", "Fiber", "EOL", "Core", "Preset", "APO"]:
        result = "Abnormal" if _has_abnormal(all_abnormal.get(key, {})) else "Normal"
        rows.append((type_map[key], task_map[key], details_map[key], result))
    return rows


def generate_report(all_abnormal: dict):
    """
    สร้าง PDF Report รวม FAN + CPU + MSU + Line + Client + Fiber + EOL + Core
    """

    # ===== Buffer & Document =====
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                           leftMargin=0.5*inch, rightMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)

    styles = getSampleStyleSheet()

    # ===== Custom Styles (ปรับขนาดตัวหนังสือ) =====
    title_center = ParagraphStyle(
        "TitleCenter", parent=styles["Heading1"], alignment=1, spaceAfter=20,
        fontSize=24, textColor=HexColor("#1f77b4")  # ลดจาก 28 → 24
    )
    date_center = ParagraphStyle(
        "DateCenter", parent=styles["Normal"], alignment=1, spaceAfter=12,
        fontSize=12, textColor=HexColor("#666666")  # ลดจาก 14 → 12
    )
    section_title_left = ParagraphStyle(
        "SectionTitleLeft", parent=styles["Heading2"], alignment=0, spaceAfter=6,
        fontSize=16, textColor=HexColor("#2c3e50")  # ลดจาก 20 → 16
    )
    normal_left = ParagraphStyle(
        "NormalLeft", parent=styles["Normal"], alignment=0, spaceAfter=12,
        fontSize=10  # ลดจาก 12 → 10
    )
    # summary_style = ParagraphStyle(
    #     "SummaryStyle", parent=styles["Normal"], alignment=1, spaceAfter=20,
    #     fontSize=14, textColor=HexColor("#27ae60")  # ลดจาก 16 → 14
    # )

    elements = []

    # ===== Title & Date =====
    elements.append(Paragraph("🌐 3BB Network Inspection Report", title_center))
    elements.append(Paragraph(f"📅 Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_center))
    elements.append(Spacer(1, 18))

    # ===== Summary Table (replace Executive Summary) =====
    elements.append(Paragraph("Summary Table", section_title_left))

    base_para = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=12)  # ลดจาก 11 → 9
    base_para.alignment = 0  # left

    summary_rows = _build_summary_rows(all_abnormal)
    # Build DataFrame for consistent rendering
    df_summary = pd.DataFrame(summary_rows, columns=["Type", "Task", "Details", "Results"])

    # Convert Results to colored Paragraphs
    table_data = [[Paragraph("Type", base_para), Paragraph("Task", base_para), Paragraph("Details", base_para), Paragraph("Results", base_para)]]
    for _, r in df_summary.iterrows():
        color = "#0F7B3E" if r["Results"] == "Normal" else "#B00020"
        table_data.append([
            Paragraph(str(r["Type"]), base_para),
            Paragraph(str(r["Task"]), base_para),
            Paragraph(str(r["Details"]), base_para),
            _colored(str(r["Results"]), color, base_para),
        ])

    # Wider Details column to improve readability
    summary_col_widths = [80, 110, 430, 80]
    summary_tbl = Table(table_data, repeatRows=1, colWidths=summary_col_widths)
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),  # ลดจาก 12 → 10
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),  # เพิ่ม padding
        ("TOPPADDING", (0, 0), (-1, -1), 6),     # เพิ่ม padding
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),  # เพิ่ม padding
    ]))
    elements.append(summary_tbl)
    elements.append(Spacer(1, 18))
    
    # ===== Page Break หลัง Summary Table (หน้าแรกมีแค่ summary) =====
    elements.append(PageBreak())

    # ===== Sections (CPU มาก่อน FAN) =====
    section_order = ["CPU", "FAN", "MSU", "Line", "Client", "Fiber", "EOL", "Core", "Preset", "APO"]
    light_red = HexColor("#FF9999")
    # light_yellow = HexColor("#FFF3CD")
    text_black = colors.black

    for section_name in section_order:
        abn_dict = all_abnormal.get(section_name, {})

        # ข้าม sections ที่ไม่มี abnormal data
        if not abn_dict:
            continue
            
        # ตรวจสอบว่ามี abnormal data จริงหรือไม่
        has_abnormal_data = False
        for subtype, data in abn_dict.items():
            # รองรับทั้ง DataFrame และ String (สำหรับ APO)
            if isinstance(data, pd.DataFrame) and not data.empty:
                has_abnormal_data = True
                break
            elif isinstance(data, str) and data.strip():
                has_abnormal_data = True
                break
                
        # ข้าม sections ที่ไม่มี abnormal data จริง
        if not has_abnormal_data:
            continue

        # Title แยกตาม type
        if section_name in ["Preset", "APO"]:
            title = f"{section_name} Analysis"
        else:
            title = f"{section_name} Performance"
        elements.append(Paragraph(title, section_title_left))

        # ===== Special handling for Fiber Flapping (group by date) =====
        if section_name == "Fiber":
            # รวม DataFrame จากทุก subtype
            all_fiber_df = []
            for subtype, df in abn_dict.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    all_fiber_df.append(df)
            
            if all_fiber_df:
                df_all = pd.concat(all_fiber_df, ignore_index=True)
                df_all["Date"] = pd.to_datetime(df_all["Begin Time"]).dt.date
                
                # เรียงตามวัน (เก่า -> ใหม่)
                dates_sorted = sorted(df_all["Date"].unique())
                
                for date in dates_sorted:
                    df_day = df_all[df_all["Date"] == date].copy()
                    num_sites = df_day["ME"].nunique() if "ME" in df_day.columns else len(df_day)
                    
                    # สรุปจำนวน flapping ต่อ Site Name เรียงจากมากไปน้อย
                    site_counts_str = ""
                    if not df_day.empty and "Site Name" in df_day.columns:
                        counts = df_day["Site Name"].value_counts().reset_index()
                        counts.columns = ["Site Name", "Count"]
                        
                        # สร้างข้อความรวมในบรรทัดเดียว เช่น Jasmine_Z-E33 (3 links)
                        site_counts_str = " ".join([
                            f"{row['Site Name']} ({row['Count']} link{'s' if row['Count'] > 1 else ''})"
                            for _, row in counts.iterrows()
                        ])
                    
                    # หัวข้อวัน + รายชื่อไซต์
                    title_text = f"Fiber Flapping – {date} ({num_sites} sites) {site_counts_str}"
                    elements.append(Paragraph(title_text, section_title_left))
                    elements.append(Spacer(1, 6))
                    
                    df_show = df_day.copy()
                    
                    # เลือกคอลัมน์
                    cols_to_show = [
                        "Begin Time", "End Time", "Site Name", "ME", "Measure Object",
                        "Max Value of Input Optical Power(dBm)",
                        "Min Value of Input Optical Power(dBm)",
                        "Input Optical Power(dBm)", "Max - Min (dB)"
                    ]
                    df_show = df_show[[c for c in cols_to_show if c in df_show.columns]]
                    
                    # แปลงคอลัมน์ตัวเลขและ format ทศนิยม 2 ตำแหน่ง
                    numeric_cols = [
                        "Max Value of Input Optical Power(dBm)",
                        "Min Value of Input Optical Power(dBm)",
                        "Input Optical Power(dBm)", 
                        "Max - Min (dB)"
                    ]
                    for col in numeric_cols:
                        if col in df_show.columns:
                            df_show[col] = pd.to_numeric(df_show[col], errors="coerce")
                            # Format เป็นทศนิยม 2 ตำแหน่ง
                            df_show[col] = df_show[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")
                    
                    # Build table
                    if not df_show.empty:
                        table_data = _df_to_wrapped_table(df_show, ParagraphStyle("Tbl", parent=styles["Normal"], fontSize=8, leading=11))  # ลดจาก 10 → 8
                        table = Table(table_data, repeatRows=1)
                        
                        style_cmds = [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),  # ลดจาก 10 → 8
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                            ("WORDWRAP", (0, 0), (-1, -1), True),
                        ]
                        
                        # Highlight Max - Min (dB) column
                        if "Max - Min (dB)" in cols_to_show:
                            col_idx = cols_to_show.index("Max - Min (dB)")
                            if col_idx < len(df_show.columns):
                                style_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, -1), light_red))
                                style_cmds.append(("TEXTCOLOR", (col_idx, 1), (col_idx, -1), text_black))
                        
                        table.setStyle(TableStyle(style_cmds))
                        elements.append(table)
                        elements.append(Spacer(1, 18))
            continue  # Skip normal processing for Fiber
        
        # ===== Special handling for APO Remnant (text summary) =====
        if section_name == "APO":
            for subtype, data in abn_dict.items():
                if isinstance(data, str) and data.strip():
                    # APO data เป็น text summary
                    # แยกออกเป็นบรรทัด แล้วแปลงเป็น Paragraph
                    lines = data.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            elements.append(Spacer(1, 6))
                            continue
                        
                        # Site header - เพิ่มขนาดตัวหนังสือสำหรับ APO
                        if line.startswith("**Site:"):
                            site_text = line.replace("**", "").replace("Site:", "Site:")
                            elements.append(Paragraph(site_text, ParagraphStyle(
                                "SiteHeader", parent=styles["Normal"], 
                                fontSize=16, textColor=HexColor("#1f77b4"),  # เพิ่มจาก 14 → 16
                                spaceAfter=6, fontName="Helvetica-Bold"
                            )))
                        # Link header - เพิ่มขนาดตัวหนังสือสำหรับ APO
                        elif line.startswith("**") and "→" in line:
                            link_text = line.replace("**", "")
                            elements.append(Paragraph(f"   {link_text}", ParagraphStyle(
                                "LinkHeader", parent=styles["Normal"], 
                                fontSize=14, textColor=HexColor("#2c3e50"),  # เพิ่มจาก 12 → 14
                                spaceAfter=4, fontName="Helvetica-Bold",
                                leftIndent=20
                            )))
                        # Code block lines (APOPLUS data) - เพิ่มขนาดตัวหนังสือสำหรับ APO
                        elif line.startswith("```"):
                            continue  # Skip markdown code fences
                        elif "[APOPLUS]" in line:
                            # แสดงเป็น monospace text
                            elements.append(Paragraph(f"      {line}", ParagraphStyle(
                                "CodeLine", parent=styles["Normal"],
                                fontSize=11, fontName="Courier",  # เพิ่มจาก 9 → 11
                                leftIndent=40, spaceAfter=2
                            )))
                    
                    elements.append(Spacer(1, 12))
            continue  # Skip normal processing for APO

        for subtype, df in abn_dict.items():
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue

            # Deduplicate Fiber Break tables: if EOL Fiber Break exists, skip Core Fiber Break table
            if section_name == "Core" and subtype == "Core Fiber Break":
                eol_break = all_abnormal.get("EOL", {}).get("EOL Fiber Break")
                if isinstance(eol_break, pd.DataFrame) and not eol_break.empty:
                    continue

            # Section Title
            elements.append(Paragraph(f"{subtype} – Abnormal Rows", section_title_left))
            elements.append(Spacer(1, 6))

            df_show = df.copy()

            # ===== Filter columns =====
            if section_name == "FAN":
                cols_to_show = [
                    "Site Name", "ME", "Measure Object",
                    "Maximum threshold", "Minimum threshold",
                    "Value of Fan Rotate Speed(Rps)"
                ]
                df_show = df_show[[c for c in cols_to_show if c in df_show.columns]]

            elif section_name == "CPU":
                cols_to_show = [
                    "Site Name", "ME", "Measure Object",
                    "Maximum threshold", "Minimum threshold",
                    "CPU utilization ratio"
                ]
                df_show = df_show[[c for c in cols_to_show if c in df_show.columns]]

            elif section_name == "MSU":
                cols_to_show = [
                    "Site Name", "ME", "Measure Object",
                    "Maximum threshold", "Laser Bias Current(mA)"
                ]
                df_show = df_show[[c for c in cols_to_show if c in df_show.columns]]

            elif section_name == "Client":
                cols_to_show = [
                    "Site Name", "ME", "Measure Object",
                    "Maximum threshold(out)", "Minimum threshold(out)", "Output Optical Power (dBm)",
                    "Maximum threshold(in)", "Minimum threshold(in)", "Input Optical Power(dBm)"
                ]
                df_show = df_show[[c for c in cols_to_show if c in df_show.columns]]

            elif section_name == "Line":
                cols_to_show = [
                    "Site Name", "ME", "Call ID", "Measure Object",
                    "Threshold", "Instant BER After FEC",
                    "Maximum threshold(out)", "Minimum threshold(out)", "Output Optical Power (dBm)",
                    "Maximum threshold(in)", "Minimum threshold(in)", "Input Optical Power(dBm)",
                    "Route"
                ]
                df_show = df_show[[c for c in cols_to_show if c in df_show.columns]]

            elif section_name == "EOL":
                cols_to_show = [
                    "Link Name", "EOL(dB)", "Current Attenuation(dB)",
                    "Loss current - Loss EOL", "Remark"
                ]
                df_show = df_show[[c for c in cols_to_show if c in df_show.columns]]

            elif section_name == "Core":
                cols_to_show = [
                    "Link Name", "Loss between core"
                ]
                df_show = df_show[[c for c in cols_to_show if c in df_show.columns]]
            
            elif section_name == "Preset":
                cols_to_show = [
                    "Call", "IP", "Preroute", "Verdict", "Status"
                ]
                df_show = df_show[[c for c in cols_to_show if c in df_show.columns]]

            # ===== Build table_data =====
            if df_show.empty:
                elements.append(Paragraph("⚠️ Data exists but no valid columns to display.", normal_left))
                elements.append(Spacer(1, 12))
                continue

            # Format numeric columns with special handling for Threshold and BER
            numeric_columns = [
                "CPU utilization ratio", "Value of Fan Rotate Speed(Rps)", "Laser Bias Current(mA)",
                "Output Optical Power (dBm)", "Input Optical Power(dBm)", "Instant BER After FEC",
                "Maximum threshold", "Minimum threshold", "Maximum threshold(out)", 
                "Minimum threshold(out)", "Maximum threshold(in)", "Minimum threshold(in)",
                "Loss current - Loss EOL", "Loss between core", "EOL(dB)", "Current Attenuation(dB)"
            ]
            
            for col in numeric_columns:
                if col in df_show.columns:
                    df_show[col] = pd.to_numeric(df_show[col], errors="coerce")
                    # Format เป็นทศนิยม 2 ตำแหน่ง
                    df_show[col] = df_show[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")
            
            # Special formatting for Threshold and Instant BER After FEC
            if "Threshold" in df_show.columns:
                df_show["Threshold"] = pd.to_numeric(df_show["Threshold"], errors="coerce")
                # Format Threshold เป็น scientific notation
                df_show["Threshold"] = df_show["Threshold"].apply(
                    lambda x: f"{x:.2E}" if pd.notna(x) else ""
                )
            
            if "Instant BER After FEC" in df_show.columns:
                df_show["Instant BER After FEC"] = pd.to_numeric(df_show["Instant BER After FEC"], errors="coerce")
                # Format BER เป็น scientific notation
                df_show["Instant BER After FEC"] = df_show["Instant BER After FEC"].apply(
                    lambda x: f"{x:.2E}" if pd.notna(x) else ""
                )

            # Convert to wrapped Paragraph cells so long text breaks into new lines
            table_data = _df_to_wrapped_table(df_show, ParagraphStyle("Tbl", parent=styles["Normal"], fontSize=8, leading=11))  # ลดจาก 10 → 8
            table = Table(table_data, repeatRows=1)

            style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),  # ลดจาก 10 → 8
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("WORDWRAP", (0, 0), (-1, -1), True),
            ]

            # ===== Highlight logic =====
            if section_name == "CPU" and "CPU utilization ratio" in cols_to_show:
                col_idx = cols_to_show.index("CPU utilization ratio")
                if col_idx < len(df_show.columns):
                    style_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, -1), light_red))
                    style_cmds.append(("TEXTCOLOR", (col_idx, 1), (col_idx, -1), text_black))

            elif section_name == "FAN" and "Value of Fan Rotate Speed(Rps)" in cols_to_show:
                col_idx = cols_to_show.index("Value of Fan Rotate Speed(Rps)")
                if col_idx < len(df_show.columns):
                    style_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, -1), light_red))
                    style_cmds.append(("TEXTCOLOR", (col_idx, 1), (col_idx, -1), text_black))

            elif section_name == "MSU" and "Laser Bias Current(mA)" in cols_to_show:
                col_idx = cols_to_show.index("Laser Bias Current(mA)")
                if col_idx < len(df_show.columns):
                    style_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, -1), light_red))
                    style_cmds.append(("TEXTCOLOR", (col_idx, 1), (col_idx, -1), text_black))

          
          
            elif section_name == "Client":
                nrows = len(df_show) + 1   # header + data
                ncols = len(df_show.columns)
                col_map = {c: i for i, c in enumerate(df_show.columns)}  # ✅ สร้าง map คอลัมน์จริง

                for ridx, row in df_show.iterrows():
                    # Output check
                    try:
                        v = float(row.get("Output Optical Power (dBm)", float("nan")))
                        lo = float(row.get("Minimum threshold(out)", float("nan")))
                        hi = float(row.get("Maximum threshold(out)", float("nan")))
                        if pd.notna(v) and pd.notna(lo) and pd.notna(hi) and (v < lo or v > hi):
                            cidx = col_map.get("Output Optical Power (dBm)")
                            if cidx is not None and 0 <= cidx < ncols and 0 <= ridx+1 < nrows:
                                style_cmds.append(("BACKGROUND", (cidx, ridx+1), (cidx, ridx+1), light_red))
                                style_cmds.append(("TEXTCOLOR", (cidx, ridx+1), (cidx, ridx+1), text_black))
                    except (ValueError, TypeError):
                        pass

                    # Input check
                    try:
                        v = float(row.get("Input Optical Power(dBm)", float("nan")))
                        lo = float(row.get("Minimum threshold(in)", float("nan")))
                        hi = float(row.get("Maximum threshold(in)", float("nan")))
                        if pd.notna(v) and pd.notna(lo) and pd.notna(hi) and (v < lo or v > hi):
                            cidx = col_map.get("Input Optical Power(dBm)")
                            if cidx is not None and 0 <= cidx < ncols and 0 <= ridx+1 < nrows:
                                style_cmds.append(("BACKGROUND", (cidx, ridx+1), (cidx, ridx+1), light_red))
                                style_cmds.append(("TEXTCOLOR", (cidx, ridx+1), (cidx, ridx+1), text_black))
                    except (ValueError, TypeError):
                        pass

            elif section_name == "Line":
                nrows = len(df_show) + 1   # header + data
                ncols = len(df_show.columns)
                col_map = {c: i for i, c in enumerate(df_show.columns)}

                for ridx, row in df_show.iterrows():
                    # BER check
                    try:
                        ber = float(row.get("Instant BER After FEC", float("nan")))
                        thr = float(row.get("Threshold", float("nan")))
                        if pd.notna(ber) and pd.notna(thr) and ber > thr:
                            cidx = col_map.get("Instant BER After FEC")
                            if cidx is not None and 0 <= cidx < ncols and 0 <= ridx+1 < nrows:
                                style_cmds.append(("BACKGROUND", (cidx, ridx+1), (cidx, ridx+1), light_red))
                                style_cmds.append(("TEXTCOLOR", (cidx, ridx+1), (cidx, ridx+1), text_black))
                    except (ValueError, TypeError):
                        pass

                    # Input check
                    try:
                        v = float(row.get("Input Optical Power(dBm)", float("nan")))
                        lo = float(row.get("Minimum threshold(in)", float("nan")))
                        hi = float(row.get("Maximum threshold(in)", float("nan")))
                        if pd.notna(v) and pd.notna(lo) and pd.notna(hi) and (v < lo or v > hi):
                            cidx = col_map.get("Input Optical Power(dBm)")
                            if cidx is not None and 0 <= cidx < ncols and 0 <= ridx+1 < nrows:
                                style_cmds.append(("BACKGROUND", (cidx, ridx+1), (cidx, ridx+1), light_red))
                                style_cmds.append(("TEXTCOLOR", (cidx, ridx+1), (cidx, ridx+1), text_black))
                    except (ValueError, TypeError):
                        pass

                    # Output check
                    try:
                        v = float(row.get("Output Optical Power (dBm)", float("nan")))
                        lo = float(row.get("Minimum threshold(out)", float("nan")))
                        hi = float(row.get("Maximum threshold(out)", float("nan")))
                        if pd.notna(v) and pd.notna(lo) and pd.notna(hi) and (v < lo or v > hi):
                            cidx = col_map.get("Output Optical Power (dBm)")
                            if cidx is not None and 0 <= cidx < ncols and 0 <= ridx+1 < nrows:
                                style_cmds.append(("BACKGROUND", (cidx, ridx+1), (cidx, ridx+1), light_red))
                                style_cmds.append(("TEXTCOLOR", (cidx, ridx+1), (cidx, ridx+1), text_black))
                    except (ValueError, TypeError):
                        pass

            elif section_name == "EOL" and "Loss current - Loss EOL" in cols_to_show:
                col_idx = cols_to_show.index("Loss current - Loss EOL")
                if col_idx < len(df_show.columns):
                    style_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, -1), light_red))
                    style_cmds.append(("TEXTCOLOR", (col_idx, 1), (col_idx, -1), text_black))

            elif section_name == "Core" and "Loss between core" in cols_to_show:
                col_idx = cols_to_show.index("Loss between core")
                if col_idx < len(df_show.columns):
                    style_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, -1), light_red))
                    style_cmds.append(("TEXTCOLOR", (col_idx, 1), (col_idx, -1), text_black))
            
            # ===== Highlight specific columns for Fiber and Line sections =====
            elif section_name == "Fiber" and "Max - Min (dB)" in cols_to_show:
                # Highlight Max - Min (dB) column for Fiber section
                col_idx = cols_to_show.index("Max - Min (dB)")
                if col_idx < len(df_show.columns):
                    style_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, -1), light_red))
                    style_cmds.append(("TEXTCOLOR", (col_idx, 1), (col_idx, -1), text_black))
            
            elif section_name == "Line" and "Instant BER After FEC" in cols_to_show:
                # Highlight Instant BER After FEC column for Line section
                col_idx = cols_to_show.index("Instant BER After FEC")
                if col_idx < len(df_show.columns):
                    style_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, -1), light_red))
                    style_cmds.append(("TEXTCOLOR", (col_idx, 1), (col_idx, -1), text_black))
            
            elif section_name == "Preset":
                # Highlight rows where Status contains "Abnormal"
                if "Status" in df_show.columns:
                    col_idx = list(df_show.columns).index("Status")
                    for ridx, row in enumerate(df_show.itertuples(index=False), start=1):
                        try:
                            status_val = str(getattr(row, "Status", ""))
                            if "Abnormal" in status_val:
                                # Highlight entire row
                                style_cmds.append(("BACKGROUND", (0, ridx), (-1, ridx), light_red))
                                style_cmds.append(("TEXTCOLOR", (0, ridx), (-1, ridx), text_black))
                        except:
                            pass

            # ===== Apply style & append =====
            table.setStyle(TableStyle(style_cmds))
            elements.append(table)
            elements.append(Spacer(1, 18))

    # ===== Build Document =====
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
