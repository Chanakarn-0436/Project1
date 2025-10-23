import re
from collections import OrderedDict  # NEW: สำหรับเก็บตารางรายวันแบบเรียงลำดับ
import pandas as pd
import streamlit as st
import plotly.express as px
from utils.filters import cascading_filter

# หมายเหตุ: ต้องมีฟังก์ชัน cascading_filter(df, cols, ns, labels=None, clear_text="...") อยู่ภายนอกให้เรียกใช้งานได้


class FiberflappingAnalyzer:
    """
    จัดระเบียบ logic สำหรับ Fiber Flapping:
      - เตรียม/normalize ข้อมูล OSC Optical และ FM
      - กรองรายการที่ Max-Min(dB) > threshold
      - หาแถวที่ 'ไม่เจอ alarm match'
      - เพิ่ม Site Name จาก reference file
      - เรนเดอร์ตาราง highlight + KPI รายวัน + กราฟรวม 7 วัน

    การใช้งาน:
        analyzer = FiberflappingAnalyzer(df_optical, df_fm, threshold=2.0)
        analyzer.process()
    """

    def __init__(self, df_optical: pd.DataFrame, df_fm: pd.DataFrame, threshold: float = 2.0, ref_path: str = "data/Flapping.xlsx"):
        self.df_optical_raw = df_optical
        self.df_fm_raw = df_fm
        self.threshold = threshold
        self.ref_path = ref_path
        self.df_ref = None  # Reference data for site names
        self.daily_tables = None  # NEW: เก็บผลตารางรายวันสำหรับ export/report

     

    # -------------------- Load Reference --------------------
    def _load_reference(self) -> pd.DataFrame:
        """โหลดไฟล์ reference สำหรับ site names (ลองทั้ง Flapping.xlsx และ flapping.xlsx)"""
        primary_path = self.ref_path
        try:
            df_ref = pd.read_excel(primary_path)
            df_ref.columns = df_ref.columns.str.strip()
            return df_ref
        except Exception as e_primary:
            # fallback: toggle filename case for compatibility
            alt_path = None
            if primary_path.endswith("Flapping.xlsx"):
                alt_path = primary_path.replace("Flapping.xlsx", "flapping.xlsx")
            elif primary_path.endswith("flapping.xlsx"):
                alt_path = primary_path.replace("flapping.xlsx", "Flapping.xlsx")

            if alt_path:
                try:
                    df_ref = pd.read_excel(alt_path)
                    df_ref.columns = df_ref.columns.str.strip()
                    # อัปเดต ref_path เป็นไฟล์ที่อ่านได้สำเร็จ
                    self.ref_path = alt_path
                    return df_ref
                except Exception as e_alt:
                    st.warning(f"Could not load reference file {primary_path} or fallback {alt_path}: {e_alt}")
                    return pd.DataFrame()
            else:
                st.warning(f"Could not load reference file {primary_path}: {e_primary}")
                return pd.DataFrame()

    # -------------------- Normalize / Prepare --------------------
    def normalize_optical(self) -> pd.DataFrame:
        df = self.df_optical_raw.copy()
        df.columns = df.columns.str.strip()

        # คำนวณ Max - Min (dB)
        df["Max - Min (dB)"] = (
            df["Max Value of Input Optical Power(dBm)"]
            - df["Min Value of Input Optical Power(dBm)"]
        )

        # Extract Target ME จาก Measure Object: ค่าในวงเล็บ
        def extract_target(measure_obj):
            match = re.search(r"\(([^)]+)\)", str(measure_obj))
            return match.group(1) if match else None

        df["Target ME"] = df["Measure Object"].apply(extract_target)

        # เพิ่ม Site Name จาก reference
        self.df_ref = self._load_reference()
        if not self.df_ref.empty and "ME" in self.df_ref.columns and "Site Name" in self.df_ref.columns:
            # Merge กับ reference เพื่อเพิ่ม Site Name
            df = df.merge(
                self.df_ref[["ME", "Site Name"]], 
                left_on="ME", 
                right_on="ME", 
                how="left"
            )
        else:
            # ถ้าไม่มี reference ให้ใช้ ME เป็น Site Name
            df["Site Name"] = df["ME"]

        # เวลาช่วง Begin/End
        df["Begin Time"] = pd.to_datetime(df["Begin Time"], errors="coerce")
        df["End Time"] = pd.to_datetime(df["End Time"], errors="coerce")
        return df

    def normalize_fm(self) -> tuple[pd.DataFrame, str]:
        df = self.df_fm_raw.copy()
        df.columns = df.columns.str.strip()

        df["Occurrence Time"] = pd.to_datetime(df["Occurrence Time"], errors="coerce")
        df["Clear Time"] = pd.to_datetime(df["Clear Time"], errors="coerce")

        # หา column แรกที่ขึ้นต้นด้วย "Link"
        link_cols = [c for c in df.columns if c.startswith("Link")]
        if not link_cols:
            raise ValueError("No 'Link*' column found in FM Alarm file.")
        link_col = link_cols[0]
        return df, link_col

    # -------------------- Core Filtering --------------------
    def filter_optical_by_threshold(self, df_optical_norm: pd.DataFrame) -> pd.DataFrame:
        return df_optical_norm[df_optical_norm["Max - Min (dB)"] > self.threshold].copy()

    def _check_time_overlap(self, begin_t: pd.Timestamp, end_t: pd.Timestamp, 
                           occur_time: pd.Timestamp, clear_time: pd.Timestamp) -> bool:
        """
        ตรวจสอบว่าช่วงเวลา flapping (begin_t, end_t) อยู่ในช่วงเวลา alarm (occur_time, clear_time) หรือไม่
        
        Returns:
            True ถ้าอยู่ในช่วงเวลา alarm (เป็น fiber cut)
            False ถ้าไม่อยู่ในช่วงเวลา alarm (เป็น fiber flapping)
        """
        if pd.isna(occur_time) or pd.isna(begin_t):
            return False
        
        # ถ้ามี clear_time ให้เช็กว่า begin_t อยู่ระหว่าง occur_time และ clear_time
        if pd.notna(clear_time):
            # เช็กว่ามีส่วนที่ overlap กันหรือไม่
            # overlap เกิดเมื่อ: begin_t <= clear_time และ end_t >= occur_time
            if pd.notna(end_t):
                return begin_t <= clear_time and end_t >= occur_time
            else:
                return begin_t <= clear_time and begin_t >= occur_time
        else:
            # ถ้ายังไม่มี clear_time ให้เช็กว่า begin_t >= occur_time
            return begin_t >= occur_time

    def find_nomatch(self, df_filtered: pd.DataFrame, df_fm_norm: pd.DataFrame, link_col: str) -> pd.DataFrame:
        """
        หาแถวใน df_filtered ที่เป็น Fiber Flapping (ไม่ใช่ Fiber Cut):
        
        Logic ใหม่:
        1. ดูจาก ME (ต้นทาง) และ Target ME (ปลายทาง - extract จาก Measure Object)
        2. Map กับ Link ใน FM Alarm
        3. เช็กว่าช่วงเวลาของ optical flapping อยู่ในช่วงเวลา alarm หรือไม่
           - ถ้าไม่อยู่ในช่วง → Fiber Flapping (เก็บไว้)
           - ถ้าอยู่ในช่วง → Fiber Cut (กรองออก)
        
        Note: ต้นทาง-ปลายทาง อาจสลับกันได้ ต้องเช็กทั้ง 2 ทาง
        """
        result_rows = []
        
        for _, row in df_filtered.iterrows():
            me = str(row.get("ME", ""))
            target_me = str(row.get("Target ME", ""))
            begin_t = row.get("Begin Time", pd.NaT)
            end_t = row.get("End Time", pd.NaT)
            
            if not me or not target_me or pd.isna(begin_t):
                continue
            
            # หา FM alarms ที่ Link contains ทั้ง ME และ Target ME (ไม่สนใจลำดับ)
            me_escaped = re.escape(me)
            target_escaped = re.escape(target_me)
            
            matched_alarms = df_fm_norm[
                (df_fm_norm[link_col].astype(str).str.contains(me_escaped, na=False) &
                 df_fm_norm[link_col].astype(str).str.contains(target_escaped, na=False))
            ]
            
            # ถ้าไม่เจอ Link ที่ match เลย → เป็น Fiber Flapping
            if matched_alarms.empty:
                result_rows.append(row)
                continue
            
            # ถ้าเจอ Link ที่ match → เช็กว่าช่วงเวลาตรงกันหรือไม่
            is_fiber_cut = False
            for _, alarm in matched_alarms.iterrows():
                occur_time = alarm.get("Occurrence Time", pd.NaT)
                clear_time = alarm.get("Clear Time", pd.NaT)
                
                # ถ้าช่วงเวลา overlap กัน → เป็น Fiber Cut
                if self._check_time_overlap(begin_t, end_t, occur_time, clear_time):
                    is_fiber_cut = True
                    break
            
            # ถ้าไม่ overlap กับ alarm ใดๆ → เป็น Fiber Flapping
            if not is_fiber_cut:
                result_rows.append(row)

        return pd.DataFrame(result_rows)

    # -------------------- View Preparation --------------------
    @staticmethod
    def prepare_view(df_nomatch: pd.DataFrame) -> pd.DataFrame:
        # คอลัมน์ที่จะโชว์ - เพิ่ม Site Name ระหว่าง Granularity และ ME
        view_cols = [
            "Begin Time", "End Time", "Granularity", "Site Name", "ME", "ME IP", "Measure Object",
            "Max Value of Input Optical Power(dBm)", "Min Value of Input Optical Power(dBm)",
            "Input Optical Power(dBm)", "Max - Min (dB)"
        ]
        view_cols = [c for c in view_cols if c in df_nomatch.columns]
        df_view = df_nomatch[view_cols].copy()

        # แปลงตัวเลขเพื่อ format ทศนิยม
        num_cols = [
            "Max Value of Input Optical Power(dBm)",
            "Min Value of Input Optical Power(dBm)",
            "Input Optical Power(dBm)",
            "Max - Min (dB)"
        ]
        num_cols = [c for c in num_cols if c in df_view.columns]
        if num_cols:
            df_view.loc[:, num_cols] = df_view[num_cols].apply(pd.to_numeric, errors="coerce")
        return df_view

    # -------------------- Rendering --------------------
    def render(self, df_nomatch: pd.DataFrame) -> None:
        st.markdown("### OSC Power Flapping (No Alarm Match)")

        if df_nomatch.empty:
            st.success("No unmatched fiber flapping records found")
            return

        # Cascading filter
        df_nomatch_filtered, _sel = cascading_filter(
            df_nomatch,
            cols=["Site Name", "ME", "Measure Object"],
            ns="fiber",
            labels={"Site Name": "Site Name", "ME": "Managed Element"},
            clear_text="Clear Fiber Filters",
        )
        st.caption(f"Fiber Flapping (showing {len(df_nomatch_filtered)}/{len(df_nomatch)} rows)")

        # เตรียมตารางแสดงผล
        df_view = self.prepare_view(df_nomatch_filtered)

        # Highlight เฉพาะคอลัมน์ "Max - Min (dB)" > threshold
        if "Max - Min (dB)" in df_view.columns:
            styled_df = (
                df_view.style
                .apply(
                    lambda _:
                        ['background-color:#ff4d4d; color:white' if (v > self.threshold) else ''
                         for v in df_view["Max - Min (dB)"]],
                    subset=["Max - Min (dB)"]
                )
                .format({
                    "Max Value of Input Optical Power(dBm)": "{:.2f}",
                    "Min Value of Input Optical Power(dBm)": "{:.2f}",
                    "Input Optical Power(dBm)": "{:.2f}",
                    "Max - Min (dB)": "{:.2f}",
                })
            )
            st.write(styled_df)
            
        else:
            st.dataframe(df_view, use_container_width=True)
        
        # คืนค่า view
        return df_view

    # -------------------- Weekly KPI (7-Day Summary) --------------------
    def render_weekly_summary(self, df_nomatch: pd.DataFrame) -> None:
        """Summary KPI: Flapping sites per day (7-day view with drill-down + graph at the end)"""
        if df_nomatch.empty:
            st.success("No unmatched fiber flapping records in past 7 days")
            return

        df_nomatch = df_nomatch.copy()
        df_nomatch["Date"] = pd.to_datetime(df_nomatch["Begin Time"]).dt.date

        # หาช่วงวัน start → end
        start_date = df_nomatch["Date"].min()
        end_date   = df_nomatch["Date"].max()
        st.markdown(f"### Fiber Flapping Summary (Past 7 Days: {start_date} → {end_date})")

        # นับจำนวน site ต่อวัน
        daily_counts = (
            df_nomatch.groupby("Date")["ME"].nunique().reset_index()
            .rename(columns={"ME": "Sites"})
        )

        # เก็บวันที่เลือก
        if "selected_day" not in st.session_state:
            st.session_state["selected_day"] = None

        # การ์ดรายวัน
        cols = st.columns(len(daily_counts))
        for i, row in daily_counts.iterrows():
            day = row["Date"]
            count = row["Sites"]
            with cols[i]:
                st.metric(label=str(day), value=f"{count} sites")
                if st.button("Show Details", key=f"btn_{day}"):
                    st.session_state["selected_day"] = day

        # Drill-down ตาราง
        if st.session_state["selected_day"]:
            sel_day = st.session_state["selected_day"]
            sel = df_nomatch[df_nomatch["Date"] == sel_day]

            # สรุปจำนวน flapping ต่อ Site Name เรียงจากมากไปน้อย
            if not sel.empty and "Site Name" in sel.columns:
                counts = sel["Site Name"].value_counts().reset_index()
                counts.columns = ["Site Name", "Count"]
                num_sites = len(counts)
                
                # แสดงหัวข้อพร้อมจำนวนไซต์
                st.markdown(f"#### {sel_day} {num_sites} sites")
                
                # สร้างข้อความรวมในบรรทัดเดียว เช่น Wiang Sra_Z (2 links)
                counts_str = " ".join([
                    f"{r['Site Name']} ({r['Count']} link{'s' if r['Count'] > 1 else ''})"
                    for _, r in counts.iterrows()
                ])
                st.markdown(counts_str)
            else:
                st.markdown(f"#### {sel_day} 0 sites")
                
            if sel.empty:
                st.info("No flapping records on this day")
            else:
                # ✅ เลือกเฉพาะคอลัมน์ที่ต้องการ (ไม่มี Target ME, Date)
                view_cols = [
                    "Begin Time", "End Time","Site Name", "ME", "ME IP", "Measure Object",
                    "Max Value of Input Optical Power(dBm)",
                    "Min Value of Input Optical Power(dBm)", "Max - Min (dB)"
                ]
                view_cols = [c for c in view_cols if c in sel.columns]
                sel = sel[view_cols]

                # ✅ ทำ highlight คอลัมน์ Max - Min (dB)
                if "Max - Min (dB)" in sel.columns:
                    styled_sel = (
                        sel.style
                        .apply(
                            lambda _:
                                ['background-color:#ff4d4d; color:white' if (v > self.threshold) else ''
                                for v in sel["Max - Min (dB)"]],
                            subset=["Max - Min (dB)"]
                        )
                        .format({
                            "Max Value of Input Optical Power(dBm)": "{:.2f}",
                            "Min Value of Input Optical Power(dBm)": "{:.2f}",
                            "Max - Min (dB)": "{:.2f}",
                        })
                    )
                    st.write(styled_sel)
                else:
                    st.dataframe(sel, use_container_width=True)
                    

        # 📊 กราฟรวม (ท้ายสุด)
        if not daily_counts.empty:
            fig = px.bar(daily_counts, x="Date", y="Sites", text="Sites", title="No Fiber Break Alarm Match(Fiber Flapping)")
            fig.update_traces(textposition="outside")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    # -------------------- Export helper (NEW) --------------------
    @staticmethod
    def _select_view_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        เลือกคอลัมน์ให้เหมือน drill-down แล้วจัดรูปตัวเลข (ใช้สำหรับ export/report)
        """
        view_cols = [
            "Begin Time", "End Time", "Site Name", "ME", "Measure Object",
            "Max Value of Input Optical Power(dBm)",
            "Min Value of Input Optical Power(dBm)",
            "Input Optical Power(dBm)", "Max - Min (dB)"
        ]
        have = [c for c in view_cols if c in df.columns]
        out = df[have].copy()

        num_cols = [c for c in [
            "Max Value of Input Optical Power(dBm)",
            "Min Value of Input Optical Power(dBm)",
            "Input Optical Power(dBm)", "Max - Min (dB)"
        ] if c in out.columns]
        if num_cols:
            out.loc[:, num_cols] = out[num_cols].apply(pd.to_numeric, errors="coerce").round(2)
        return out

    def build_daily_tables(self, df_nomatch: pd.DataFrame) -> "OrderedDict[str, pd.DataFrame]":
        """
        สร้าง dict รายวัน -> DataFrame (คอลัมน์เหมือน drill-down) สำหรับ export
        เช่น {"2025-06-17": df_table, "2025-06-18": df_table, ...}
        """
        if df_nomatch.empty:
            self.daily_tables = OrderedDict()
            return self.daily_tables

        df = df_nomatch.copy()
        df["Date"] = pd.to_datetime(df["Begin Time"]).dt.date

        tables = OrderedDict()
        for day, g in df.sort_values("Begin Time").groupby("Date", sort=True):
            tables[str(day)] = self._select_view_columns(g)
        self.daily_tables = tables
        return tables

    # -------------------- Orchestration --------------------
    def process(self) -> None:
        # 1) เตรียมข้อมูล
        df_optical_norm = self.normalize_optical()
        df_fm_norm, link_col = self.normalize_fm()

        # 2) กรองตาม threshold
        df_filtered = self.filter_optical_by_threshold(df_optical_norm)

        # 3) หา no-match
        df_nomatch = self.find_nomatch(df_filtered, df_fm_norm, link_col)

        # 4) ตารางหลัก
        self.render(df_nomatch)

        # 5) Weekly Summary KPI + กราฟท้ายสุด
        self.render_weekly_summary(df_nomatch)

    def prepare(self) -> None:
        """
        เตรียมข้อมูลสำหรับ Summary/PDF (ไม่ render UI)
        """
        # 1) เตรียมข้อมูล
        df_optical_norm = self.normalize_optical()
        df_fm_norm, link_col = self.normalize_fm()

        # 2) กรองตาม threshold
        df_filtered = self.filter_optical_by_threshold(df_optical_norm)

        # 3) หา no-match
        df_nomatch = self.find_nomatch(df_filtered, df_fm_norm, link_col)

        # 4) สร้าง abnormal tables
        if not df_nomatch.empty:
            df_view = self._select_view_columns(df_nomatch)
            self.df_abnormal = df_view.copy()
            self.df_abnormal_by_type = {
                "Fiber Flapping": df_view
            }
        else:
            self.df_abnormal = pd.DataFrame()
            self.df_abnormal_by_type = {}

        # 5) ตั้งค่า session_state สำหรับ sidebar indicator
        st.session_state["fiberflapping_abn_count"] = len(self.df_abnormal)
        st.session_state["fiberflapping_status"] = "Abnormal" if not self.df_abnormal.empty else "Normal"

        # 6) สร้าง daily tables สำหรับ export
        self.build_daily_tables(df_nomatch)

    @property
    def df_abnormal(self):
        return getattr(self, '_df_abnormal', pd.DataFrame())

    @df_abnormal.setter
    def df_abnormal(self, value):
        self._df_abnormal = value

    @property
    def df_abnormal_by_type(self):
        return getattr(self, '_df_abnormal_by_type', {})

    @df_abnormal_by_type.setter
    def df_abnormal_by_type(self, value):
        self._df_abnormal_by_type = value

    
