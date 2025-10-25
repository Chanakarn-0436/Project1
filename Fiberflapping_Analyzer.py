import re
from collections import OrderedDict  # NEW: สำหรับเก็บตารางรายวันแบบเรียงลำดับ
import pandas as pd
import streamlit as st
import plotly.express as px
from utils.filters import cascading_filter


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

    # -------------------- Regex --------------------
    # ดึงชื่อโหนดที่ลงท้ายด้วย _A หรือ _R เช่น CR_WCO_7807_031_1Z_A / SR_WCO_9006_043_1Z_A
    _NODE_PATTERN = re.compile(r'[A-Z]{2}_[A-Z0-9]+_\d{3,4}_[0-9]{3}_[0-9A-Z]+_[AR]')

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

    # -------------------- Helpers --------------------
    @staticmethod
    def _extract_target_from_measure_object(measure_obj: str) -> str | None:
        """ดึง Target ME จากข้อความในวงเล็บของ Measure Object"""
        m = re.search(r"\(([^)]+)\)", str(measure_obj))
        return m.group(1) if m else None

    def _extract_nodes_from_link(self, link_val: str) -> tuple[str | None, str | None]:
        """
        ดึงชื่อโหนด 2 ตัวจากคอลัมน์ Link ของ FM
        คืนค่า (fm_node1, fm_node2) หรือ (None, None) ถ้าดึงไม่ได้
        - ใช้ regex หา token ที่หน้าตาเหมือน ME/Target (ลงท้าย _A/_R)
        - เลือก 2 ตัวแรกตามลำดับที่ปรากฏ
        """
        if pd.isna(link_val):
            return (None, None)
        s = str(link_val)
        nodes = self._NODE_PATTERN.findall(s)
        if len(nodes) >= 2:
            return (nodes[0], nodes[1])
        return (None, None)

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
        df["Target ME"] = df["Measure Object"].apply(self._extract_target_from_measure_object)

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
        link_cols = [c for c in df.columns if str(c).startswith("Link")]
        if not link_cols:
            raise ValueError("No 'Link*' column found in FM Alarm file.")
        link_col = link_cols[0]

        # ✅ เตรียม fm_node1, fm_node2 เพื่อเร่งความเร็วขณะเทียบ
        fm_nodes = df[link_col].apply(self._extract_nodes_from_link)
        df["fm_node1"] = fm_nodes.apply(lambda x: x[0])
        df["fm_node2"] = fm_nodes.apply(lambda x: x[1])

        return df, link_col

    # -------------------- Core Filtering --------------------
    def filter_optical_by_threshold(self, df_optical_norm: pd.DataFrame) -> pd.DataFrame:
        """
        กรองข้อมูล Optical:
          1. ตัดแถวที่ Min Value = -60 (ถือว่าไม่มีสัญญาณ)
          2. เก็บเฉพาะแถวที่ Max - Min (dB) > threshold
        """
        df = df_optical_norm.copy()

        # 1️⃣ ตัดแถวที่ Min Value = -60
        if "Min Value of Input Optical Power(dBm)" in df.columns:
            before = len(df)
            df = df[df["Min Value of Input Optical Power(dBm)"] != -60]
            after = len(df)
            print(f"🔹 Filtered out {before - after} rows where Min Value = -60 dBm")

        # 2️⃣ กรองตาม threshold
        df_filtered = df[df["Max - Min (dB)"] > self.threshold].copy()

        print(f"✅ Remaining rows after threshold filter: {len(df_filtered)}")
        return df_filtered


    def find_nomatch(self, df_filtered: pd.DataFrame, df_fm_norm: pd.DataFrame, link_col: str) -> pd.DataFrame:
        """
        Logic ใหม่: ตรวจทีละแถว โดยเทียบ 'คู่โหนด' กับคอลัมน์ Link ของ FM (สลับได้)
        ถ้าไม่พบคู่โหนดใน FM → FLAPPING
        ถ้าพบคู่โหนด → ตรวจเวลา overlap:
            Occurrence Time <= End Time และ Clear Time >= Begin Time
            - ถ้ามีอย่างน้อย 1 แถว overlap → MATCHED (not flapping)
            - ถ้าไม่มี overlap เลย → FLAPPING
        พิมพ์ log ลง terminal ทุกกรณี
        """
        result_rows = []

        # เตรียมเฉพาะ FM rows ที่มีโหนดครบทั้ง 2 ข้าง
        fm_valid = df_fm_norm.dropna(subset=["fm_node1", "fm_node2"]).copy()

        for idx, row in df_filtered.reset_index(drop=True).iterrows():
            node_a = str(row.get("ME", "")).strip()
            node_b = str(row.get("Target ME", "")).strip()
            begin_t = row.get("Begin Time", pd.NaT)
            end_t = row.get("End Time", pd.NaT)

            # ข้ามแถวที่ไม่มี node ใด node หนึ่ง
            if not node_a or not node_b or pd.isna(begin_t) or pd.isna(end_t):
                print(f"Row {idx}: ⚠️ Missing fields → ME='{node_a}', Target='{node_b}', Begin='{begin_t}', End='{end_t}' → Treat as FLAPPING")
                result_rows.append(row)
                continue

            # หา FM ที่คู่โหนดตรง (สลับได้)
            fm_pair_mask = (
                ((fm_valid["fm_node1"] == node_a) & (fm_valid["fm_node2"] == node_b)) |
                ((fm_valid["fm_node1"] == node_b) & (fm_valid["fm_node2"] == node_a))
            )
            fm_candidates = fm_valid[fm_pair_mask]

           
            # ไม่เจอคู่โหนดเลย → FLAPPING
            if fm_candidates.empty:
                print(
                    f"Row {idx}: ME={node_a}, Target={node_b}\n"
                    f"       No match in FM for link pair ({node_a} ↔ {node_b})\n"
                    f"       Optical Time: {begin_t} → {end_t}\n"
                    f"       → FLAPPING ✅ (no FM link found)"
                )
                result_rows.append(row)
                continue

            # มีคู่โหนดใน FM → ตรวจเวลา overlap (มีสักอัน overlap = MATCHED)
            any_overlap = False
            multi_logs = []
            for j, fm_r in fm_candidates.iterrows():
                fm_a, fm_b = fm_r["fm_node1"], fm_r["fm_node2"]
                occ_t = fm_r.get("Occurrence Time", pd.NaT)
                clr_t = fm_r.get("Clear Time", pd.NaT)

                overlap = (
                    pd.notna(occ_t)
                    and pd.notna(clr_t)
                    and (occ_t <= end_t)
                    and (clr_t >= begin_t)
                )
                any_overlap = any_overlap or overlap

                # เก็บ log ต่อรายการ
                multi_logs.append(
                    f"           FM Link: {fm_a}-{fm_b}, FM Time: {occ_t} → {clr_t} "
                    f"({'Overlap ✅' if overlap else 'No overlap'})"
                )

            # ✅ พิมพ์เฉพาะกรณี FLAPPING เท่านั้น
            if not any_overlap:
                if len(multi_logs) == 1:
                    header = (
                        f"Row {idx}: ME={node_a}, Target={node_b}\n"
                        f"       Found match in FM → Link: {fm_candidates.iloc[0]['fm_node1']}-{fm_candidates.iloc[0]['fm_node2']}\n"
                        f"       Optical Time: {begin_t} → {end_t}\n"
                    )
                    print(header + multi_logs[0] + f"\n       Time overlap: False  → FLAPPING ✅")
                else:
                    print(
                        f"Row {idx}: ME={node_a}, Target={node_b}\n"
                        f"       Found multiple FM matches:\n" +
                        "\n".join(multi_logs) + "\n" +
                        f"       Optical Time: {begin_t} → {end_t}\n"
                        f"       Overall Result → FLAPPING ✅"
                    )

                # เก็บเข้า result ถ้า 'ไม่ overlap ทั้งหมด' = FLAPPING
                result_rows.append(row)

        return pd.DataFrame(result_rows)

    # -------------------- View Preparation --------------------
    @staticmethod
    def prepare_view(df_nomatch: pd.DataFrame) -> pd.DataFrame:
        # คอลัมน์ที่จะโชว์ - เพิ่ม Site Name ระหว่าง Granularity และ ME
        view_cols = [
            "Begin Time", "End Time", "Granularity", "Site Name", "ME", "ME IP", "Measure Object",
            "Max Value of Input Optical Power(dBm)", "Min Value of Input Optical Power(dBm)", "Max - Min (dB)"
        ]
        view_cols = [c for c in view_cols if c in df_nomatch.columns]
        df_view = df_nomatch[view_cols].copy()

        # แปลงตัวเลขเพื่อ format ทศนิยม
        num_cols = [
            "Max Value of Input Optical Power(dBm)",
            "Min Value of Input Optical Power(dBm)",
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

           
            st.markdown(f"#### Details for {sel_day}")

            # 🔹 สรุปจำนวน flapping ต่อ Site Name (แบบใหม่)
            if not sel.empty and "Site Name" in sel.columns and "ME" in sel.columns and "Measure Object" in sel.columns:
                # ดึง Target ME จาก Measure Object (ใช้ regex ดึงในกรณีที่ยังไม่มี Target ME)
                sel["Target ME"] = sel["Measure Object"].apply(
                    lambda x: re.search(r"\(([^)]+)\)", str(x)).group(1) if pd.notna(x) and re.search(r"\(([^)]+)\)", str(x)) else None
                )
                summary_rows = []
                for site, group in sel.groupby("Site Name"):
                    # สร้างชุด link ไม่ซ้ำ (ME + Target ME)
                    link_pairs = group[["ME", "Target ME"]].drop_duplicates()
                    n_links = len(link_pairs)
                    n_times = len(group)
                    summary_rows.append(f"{site} ({n_links} link{'s' if n_links > 1 else ''} {n_times} time{'s' if n_times > 1 else ''})")

                counts_str = " ".join(summary_rows)
                st.markdown(counts_str)
                
            if sel.empty:
                st.info("No flapping records on this day")
            else:
                # ✅ เลือกเฉพาะคอลัมน์ที่ต้องการ (ไม่มี Target ME, Date)
                view_cols = [
                    "Begin Time", "End Time", "Site Name", "ME", "ME IP", "Measure Object",
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
            "Max - Min (dB)"
        ]
        have = [c for c in view_cols if c in df.columns]
        out = df[have].copy()

        num_cols = [c for c in [
            "Max Value of Input Optical Power(dBm)",
            "Min Value of Input Optical Power(dBm)",
            "Max - Min (dB)"
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

        # 3) หา no-match (ด้วย logic ใหม่)
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

        # 3) หา no-match (ด้วย logic ใหม่)
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

        # 5) สร้าง daily tables สำหรับ export
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

    
