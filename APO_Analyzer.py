from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
import re
import html

import streamlit as st
import pandas as pd
import plotly.express as px



@dataclass
class _SiteBucket:
    name: str
    wason_lines: List[str] = field(default_factory=list)
    apop_lines: List[str] = field(default_factory=list)
    # (traffic_hex, conn_hex, state, raw_line)
    apop_rows: List[Tuple[str, str, str, str]] = field(default_factory=list)


class ApoRemnantAnalyzer:
    def __init__(self, raw_text: str, site_map: Dict[str, str] | None = None):
        """
        raw_text: เนื้อ log ทั้งไฟล์ (string)
        site_map: map ip → ชื่อไซต์ (ไม่ส่งมาก็มีค่า default ให้)
        """
        self.raw_text = raw_text
        self.lines = raw_text.splitlines()
        self.site_map = site_map or {
            "30.10.90.6":  "HYI-4",
            "30.10.10.6":  "Jasmine",
            "30.10.30.6":  "Phu Nga",
            "30.10.50.6":  "SNI-POI",
            "30.10.70.6":  "NKS",
            "30.10.110.6": "PKT",
        }

        # ===== regex =====
        self.re_wason_exec = re.compile(r'^\s*ZXPOTN\(.*\)#\s*exec\s+diag_c\("cc-cmd setcallcv SetupApo"\)')
        self.re_wason_end  = re.compile(r'^\[WASON\]ushell command finished\b', re.I)
        self.re_wason_conn = re.compile(r"^\[WASON\]\s*Conn\s*\[")

        self.re_apop_begin = re.compile(r'^\[APOPLUS\]\s*===\s*show all och-inst\s*===', re.I)
        self.re_apop_top   = re.compile(r'^\[APOPLUS\]\s*TopNeIp\s*:\s*([0-9\.]+)')
        self.re_apop_end   = re.compile(r'^\[APOPLUS\]ushell command finished\b', re.I)
        self.re_apop_row = re.compile(
            r"^\[APOPLUS\]\d+\s+0x[0-9a-fA-F]+\s+0x[0-9a-fA-F]+\s+(0x[0-9a-fA-F]{8})\s+(0x[0-9a-fA-F]{8}).*\b(HEAD[A-Z_]+)\b",
            re.I
        )

        # outputs
        self.per_site: Dict[str, _SiteBucket] = {}  # key: wason_first_ip
        # [(ip, (site_name, wason_snip, apop_snip, to_red_set), has_mismatch, site_name_for_sort)]
        self.rendered: List[Tuple[str, Tuple[str, str, str, Set[str]], bool, str]] = []

    # ---------- helpers ----------
    @staticmethod
    def _topne_to_wason_ip(top_ne_ip: str) -> Optional[str]:
        m = re.match(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", top_ne_ip)
        if not m:
            return None
        x = m.group(3)
        return f"30.10.{x}.6"

    @staticmethod
    def _wason_pair_for_compare(conn_line: str) -> Optional[Tuple[str, int, str]]:
        """
        [WASON] Conn [30.10.x.x 30.10.y.y CALLID CONNNO] ...
        return: (first_ip, call_id:int, conn_hex:str)
        """
        m = re.search(r"Conn\s*\[\s*([\d\.]+)\s+([\d\.]+)\s+(\d+)\s+(\d+)\s*\]", conn_line)
        if not m:
            return None
        first_ip, _second_ip, call_id_str, conn_no_str = m.groups()
        call_id = int(call_id_str)
        conn_hex = f"0x{int(conn_no_str):08x}".lower()
        return first_ip, call_id, conn_hex
    
    @staticmethod
    def _hex_to_ip(hex_str: str) -> str:
        """แปลงเลข เช่น 0x1e0a6e06 → 30.10.110.6"""
        try:
            h = hex_str.replace("0x", "").zfill(8)
            parts = [str(int(h[i:i+2], 16)) for i in range(0, 8, 2)]
            return ".".join(parts)
        except Exception:
            return hex_str    

    def _ensure_bucket(self, ip: str):
        if ip not in self.per_site:
            self.per_site[ip] = _SiteBucket(name=self.site_map.get(ip, ip))

    # ---------- ขั้นที่ 1: parse ----------
    def parse(self) -> Dict[str, _SiteBucket]:
        wason_prebuf: List[str] = []
        apop_prebuf:  List[str] = []
        cap_wason = cap_apop = False
        cur_wason_ip_ctx: Optional[str] = None
        cur_apop_site_ip: Optional[str] = None

        for ln in self.lines:
            # WASON begin / end
            if self.re_wason_exec.search(ln):
                cap_wason = True
                cur_wason_ip_ctx = None
                wason_prebuf.clear()
                wason_prebuf.append(ln)
            if self.re_wason_end.search(ln):
                if cap_wason and cur_wason_ip_ctx:
                    self.per_site[cur_wason_ip_ctx].wason_lines.append(ln)
                cap_wason = False
                cur_wason_ip_ctx = None
                wason_prebuf.clear()
                continue

            # APOP begin / end
            if self.re_apop_begin.search(ln):
                cap_apop = True
                cur_apop_site_ip = None
                apop_prebuf.clear()
                apop_prebuf.append(ln)
                continue
            if self.re_apop_end.search(ln):
                if cap_apop and cur_apop_site_ip:
                    self.per_site[cur_apop_site_ip].apop_lines.append(ln)
                cap_apop = False
                cur_apop_site_ip = None
                apop_prebuf.clear()
                continue

            # collect WASON
            if cap_wason:
                if ln.startswith("[WASON]"):
                    if cur_wason_ip_ctx is None:
                        wason_prebuf.append(ln)
                        if self.re_wason_conn.search(ln):
                            info = self._wason_pair_for_compare(ln)
                            if info:
                                first_ip, _, _ = info
                                cur_wason_ip_ctx = first_ip
                                self._ensure_bucket(first_ip)
                                self.per_site[first_ip].wason_lines.extend(wason_prebuf)
                                wason_prebuf.clear()
                    else:
                        self.per_site[cur_wason_ip_ctx].wason_lines.append(ln)
                continue

            # collect APOP
            if cap_apop and ln.startswith("[APOPLUS]"):
                if cur_apop_site_ip is None:
                    apop_prebuf.append(ln)
                    mtop = self.re_apop_top.search(ln)
                    if mtop:
                        mapped_ip = self._topne_to_wason_ip(mtop.group(1))
                        cur_apop_site_ip = mapped_ip
                        if mapped_ip:
                            self._ensure_bucket(mapped_ip)
                            self.per_site[mapped_ip].apop_lines.extend(apop_prebuf)
                            apop_prebuf.clear()
                    continue

                self.per_site[cur_apop_site_ip].apop_lines.append(ln)
                mrow = self.re_apop_row.match(ln)
                if mrow:
                    traffic = mrow.group(1).lower()
                    connno  = mrow.group(2).lower()
                    state   = mrow.group(3)
                    self.per_site[cur_apop_site_ip].apop_rows.append((traffic, connno, state, ln))
                continue

        return self.per_site

    # ---------- ขั้นที่ 2: analyze ----------
    @staticmethod
    def _traffic_hex_from(call_id: int, scheme: str) -> str:
        return f"0x{(call_id << 24):08x}" if scheme == "shifted" else f"0x{call_id:08x}"


    # --- ขั้นที่ 2: analyze ---
    def analyze(self):
        """
        วิเคราะห์ความสอดคล้องระหว่าง WASON กับ APOP:
        - แก้ bug เดิมที่ใช้ set เทียบตรง ๆ แล้วเน้นแดงผิด
        - เพิ่ม .strip().lower() เพื่อ normalize ค่า
        - เปลี่ยน logic เทียบ Case 3 ให้ไม่แดงทั้งคู่เกินเหตุ
        """
        from collections import Counter

        self.rendered.clear()

        for wip, bucket in self.per_site.items():
            site_name     = bucket.name
            wason_snippet = "\n".join(bucket.wason_lines)
            apop_snippet  = "\n".join(bucket.apop_lines)

            # -----------------------------------
            # ✅ Reset ตัวแปรใหม่ต่อ site
            # -----------------------------------
            apop_by_traffic: Dict[str, Dict[str, str]] = {}
            to_red_apop: Set[str] = set()
            to_red_wason: Set[str] = set()

            # -----------------------------------
            # ✅ Index APOP: รับเฉพาะ state ที่ต้องเทียบ
            # -----------------------------------
            valid_states = {
                "HEAD_DETECT_WAITING",
                "HEAD_POWER_ADJUSTING",
                "HEAD_ERROR_DETECTING",
            }

            for t, c, state, ln_ap in bucket.apop_rows:
                s = (state or "").upper().strip()
                t = t.strip().lower()
                c = c.strip().lower()
                if s in valid_states:
                    apop_by_traffic.setdefault(t, {})[c] = ln_ap

            # -----------------------------------
            # ✅ Collect WASON calls ของ site ปัจจุบัน
            # -----------------------------------
            wason_calls: List[Tuple[int, str, str]] = []  # (call_id, conn_hex, raw_line)
            for ln_w in bucket.wason_lines:
                if not self.re_wason_conn.search(ln_w):
                    continue
                parsed = self._wason_pair_for_compare(ln_w)
                if not parsed:
                    continue
                first_ip, call_id, c_hex = parsed
                if first_ip == wip:
                    c_hex = c_hex.strip().lower()
                    wason_calls.append((call_id, c_hex, ln_w))

            # ถ้าไม่มี WASON → ข้าม
            if not wason_calls:
                self.rendered.append((wip, (site_name, wason_snippet, apop_snippet, set(), set()), False, site_name))
                continue

            # -----------------------------------
            # ✅ scheme = direct (ZTE OTN)
            # -----------------------------------
            # --- เลือก scheme ---
            def score_scheme(scheme: str) -> int:
                return sum(self._traffic_hex_from(call_id, scheme) in apop_by_traffic for call_id, _c, _l in wason_calls)

            score_shifted = score_scheme("shifted")
            score_direct  = score_scheme("direct")
            if score_shifted == score_direct:
                shifted_like = sum(t.endswith("000000") for t in apop_by_traffic.keys())
                scheme = "shifted" if shifted_like > 0 else "direct"
            else:
                scheme = "shifted" if score_shifted > score_direct else "direct"


            # -----------------------------------
            # ✅ สร้างเซ็ตคู่ (TrafficID, ConnNo)
            # -----------------------------------
            wason_pairs = [
                (self._traffic_hex_from(call_id, scheme).strip().lower(), c_hex)
                for call_id, c_hex, _ in wason_calls
            ]
            apop_pairs = [
                (t_hex.strip().lower(), c_hex.strip().lower())
                for t_hex, conns in apop_by_traffic.items()
                for c_hex in conns.keys()
            ]

            # ✅ ใช้ Counter() เพื่อรักษาจำนวนซ้ำ
            wason_counter = Counter(wason_pairs)
            apop_counter  = Counter(apop_pairs)

            # -----------------------------------
            # ✅ เปรียบเทียบตามกติกา
            # -----------------------------------

            # Case 1️⃣ ตรงหมด → ไม่แดงเลย
            if wason_counter == apop_counter:
                has_mismatch = False

            # Case 2️⃣ APOP เกิน → แดงเฉพาะฝั่ง APOP
            elif sum(apop_counter.values()) > sum(wason_counter.values()):
                extra = apop_counter - wason_counter
                for p in extra:
                    ln = apop_by_traffic.get(p[0], {}).get(p[1])
                    if ln:
                        to_red_apop.add(ln)
                has_mismatch = bool(to_red_apop)

            # Case 3️⃣ จำนวนเท่ากันแต่ไม่ตรง → แดงเฉพาะคู่ที่ mismatch จริง
            elif sum(apop_counter.values()) == sum(wason_counter.values()) and apop_counter != wason_counter:
                mismatch_pairs = set(apop_counter.keys()) ^ set(wason_counter.keys())
                for p in mismatch_pairs:
                    if p in wason_pairs:
                        idxs = [
                                    ln for call_id, c_hex_w, ln in wason_calls
                                    if (self._traffic_hex_from(call_id, scheme).strip().lower(), c_hex_w.strip().lower()) == p
                                ]
                        to_red_wason.update(idxs)
                    if p[0] in apop_by_traffic and p[1] in apop_by_traffic[p[0]]:
                        to_red_apop.add(apop_by_traffic[p[0]][p[1]])
                has_mismatch = bool(to_red_apop or to_red_wason)

            # Case 4️⃣ WASON มีมากกว่า (APOP ขาด) → ไม่แดง
            else:
                has_mismatch = False

            # -----------------------------------
            # ✅ สรุปต่อ site
            # -----------------------------------
            self.rendered.append(
                (
                    wip,
                    (site_name, wason_snippet, apop_snippet, set(to_red_wason), set(to_red_apop)),
                    has_mismatch,
                    site_name,
                )
            )
        for wip, (site_name, _ws, _ap, _red_w, red_a), has_mismatch, _sort_name in self.rendered:
            if has_mismatch and red_a:
                print(f"\nSite: {site_name} ({wip})")

                # เก็บกลุ่มเส้นทางใน dict: { (src_label, dst_label): [lines] }
                grouped_lines = {}
                for ln in sorted(red_a):
                    m = re.search(
                        r"\[APOPLUS\](\d+)\s+(0x[0-9a-fA-F]{8})\s+(0x[0-9a-fA-F]{8})\s+(0x[0-9a-fA-F]{8})\s+(0x[0-9a-fA-F]{8})\s+(0x[0-9a-fA-F]{8})\s+(0x[0-9a-fA-F]{8})\s+(\S+)",
                        ln
                    )
                    if not m:
                        continue

                    no, src_hex, dst_hex, traffic, connno, connattr, conntype, state = m.groups()

                    # --- แปลง hex → IP ---
                    src_ip = self._hex_to_ip(src_hex)
                    dst_ip = self._hex_to_ip(dst_hex)
                    src_site = self.site_map.get(src_ip, "")
                    dst_site = self.site_map.get(dst_ip, "")

                    src_label = f"{src_site} ({src_ip})" if src_site else src_ip
                    dst_label = f"{dst_site} ({dst_ip})" if dst_site else dst_ip

                    grouped_lines.setdefault((src_label, dst_label), []).append(
                        (no, src_hex, dst_hex, traffic, connno, connattr, conntype, state)
                    )

                # ---- พิมพ์แบบกลุ่มต่อกลุ่ม ----
                for i, ((src_label, dst_label), lines) in enumerate(grouped_lines.items(), start=1):
                    print(f"   {src_label} → {dst_label}")
                    print("    [APOPLUS]No    SourceNodeID      DestNodeID      TrafficID          ConnNo        ConnAttr       ConnType                     State")
                    for no, src_hex, dst_hex, traffic, connno, connattr, conntype, state in lines:
                        print(f"    [APOPLUS]{no:<4}   {src_hex:<16} {dst_hex:<16} {traffic:<16} {connno:<14} {connattr:<14} {conntype:<14} {state}")

                    # ✅ เว้นบรรทัดหลังแต่ละกลุ่มเพื่อแยกตาราง
                    print()

        return self.rendered






    # ---------- ขั้นที่ 3: render ----------
    def render_streamlit(self, view_choice: Optional[str] = None, display_fn=None):
        self._inject_css()

        if view_choice == "APO":
            to_show = [x for x in self.rendered if x[2]]
        elif view_choice == "No APO":
            to_show = [x for x in self.rendered if not x[2]]
        else:
            to_show = self.rendered

        if not to_show:
            st.info("No data to display")
            return

        to_show.sort(key=lambda x: x[3])
        display = display_fn or self.display_logs_separate
        for _, args, _, _ in to_show:
            site_name, wason_snip, apop_snip, to_red_wason, to_red_apop = args
            display(site_name, wason_snip, apop_snip, to_red_wason, to_red_apop)



    # --- renderer ของแต่ละไซต์ ---
    def display_logs_separate(self, site_name: str, wason_text: str, apop_text: str,
                            wason_lines_to_red: Set[str], apop_lines_to_red: Set[str]):
        wason_lines = wason_text.splitlines() if wason_text else ["<i>No WASON log</i>"]
        apop_lines  = apop_text.splitlines()  if apop_text  else ["<i>No APOP log</i>"]

        wason_rows = []
        for wl in wason_lines:
            wl_html = wl if wl.startswith("<i>") else html.escape(wl)
            ws_cls = ' class="mismatch"' if wl in wason_lines_to_red else ""
            wason_rows.append(f"<tr><td{ws_cls}>{wl_html}</td></tr>")

        apop_rows = []
        for al in apop_lines:
            al_html = al if al.startswith("<i>") else html.escape(al)
            ap_cls = ' class="mismatch"' if al in apop_lines_to_red else ""
            apop_rows.append(f"<tr><td{ap_cls}>{al_html}</td></tr>")

        site_name = html.escape(site_name)
        html_block = f"""
        <div class="site-header"><div class="pill">{site_name}</div></div>
        <div class="grid-2col">
        <div class="pane">
            <div class="title">WASON</div>
            <div class="log-table-container">
            <table class="log-table"><tbody>{''.join(wason_rows)}</tbody></table>
            </div>
        </div>
        <div class="pane">
            <div class="title">APOPLUS</div>
            <div class="log-table-container">
            <table class="log-table"><tbody>{''.join(apop_rows)}</tbody></table>
            </div>
        </div>
        </div>
        """
        st.markdown(html_block, unsafe_allow_html=True)



    # --- CSS สำหรับ layout ---
    @staticmethod
    def _inject_css():
        LOG_CSS = """
        <style>
        .grid-2col{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:8px 0 22px;}
        .pane{border:1px solid #dcdcdc;border-radius:6px;background:#fff;}
        .title{font-weight:600;padding:6px 8px;border-bottom:1px solid #e7e7e7;background:#fafafa;color:#000;}
        .log-table-container{max-height:70vh;overflow:auto;background:#fff;border-radius:6px;}
        .log-table{width:100%;border-collapse:collapse;font-family:ui-monospace, Menlo, Consolas, monospace;font-size:13px;table-layout:fixed;}
        .log-table th, .log-table td{padding:4px 8px;border-bottom:1px solid #eee;vertical-align:top;text-align:left;white-space:pre;word-wrap:break-word;}
        .log-table thead th{position:sticky; top:0;background:#fafafa;z-index:1;}
        td.mismatch{background:#fee2e2;}
        .site-header{display:flex;align-items:center;gap:8px;margin:10px 0 6px;}
        .pill{background:#1f2937;color:#e5e7eb;padding:3px 8px;border-radius:999px;font-weight:600;font-size:12px}
        </style>
        """
        st.markdown(LOG_CSS, unsafe_allow_html=True)



# =========================
# Helper: KPI summary
# =========================

def apo_kpi(rendered: list[tuple]):
    """
    rendered: list ที่ได้จาก ApoRemnantAnalyzer.analyze()
    """
    # ---------- Summary Count ----------
    total_sites = len(rendered)
    apo_sites   = sum(1 for x in rendered if x[2])   # has_mismatch = True
    noapo_sites = sum(1 for x in rendered if not x[2])  # has_mismatch = False

    # ตั้งค่า session_state สำหรับ sidebar indicator
    st.session_state["apo_abn_count"] = apo_sites
    st.session_state["apo_status"] = "Abnormal" if apo_sites > 0 else "Normal"

    # ---------- KPI Cards ----------
    st.markdown("### APO Remnant Status Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Sites", f"{total_sites}")
    with col2:
        st.metric("No APO Remnant", f"{noapo_sites}")
    with col3:
        st.metric("APO Remnant", f"{apo_sites}")

    # ---------- Donut Chart ----------
    df_summary = pd.DataFrame({
        "Status": (["No APO Remnant"] * noapo_sites) + (["APO Remnant"] * apo_sites)
    })

    fig = px.pie(
        df_summary,
        names="Status",
        hole=0.5,
        color="Status",
        color_discrete_map={
            "No APO Remnant": "green",
            "APO Remnant": "red",
        }
    )
    fig.update_traces(textinfo="value+label")
    fig.add_annotation(
        dict(
        text=f"Total size<br>{total_sites}",
        x=0.5, y=0.5,
        font_size=18,
        showarrow=False,
        xanchor="center",
        yanchor="middle",
        font_color="black"
        )
    )
    st.plotly_chart(fig, use_container_width=True)
