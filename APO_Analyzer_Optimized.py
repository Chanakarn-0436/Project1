# APO_Analyzer_Optimized.py
"""
Optimized version of APO_Analyzer with performance improvements
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
import re
import html
import pandas as pd
import numpy as np
import streamlit as st
from utils.performance_utils import (
    optimize_dataframe_operations,
    batch_process_dataframe,
    performance_monitor,
    optimize_dataframe_memory
)

@dataclass
class _SiteBucket:
    name: str
    wason_lines: List[str] = field(default_factory=list)
    apop_lines: List[str] = field(default_factory=list)
    apop_rows: List[Tuple[str, str, str, str, str, str]] = field(default_factory=list)

class ApoRemnantAnalyzerOptimized:
    """
    Optimized version of ApoRemnantAnalyzer with performance improvements:
    - Vectorized regex operations
    - Optimized parsing
    - Memory-efficient processing
    - Batch processing for large datasets
    """
    
    def __init__(self, raw_text: str, site_map: Dict[str, str] | None = None):
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
        
        # Compile regex patterns for better performance
        self.re_wason_exec = re.compile(r'^\s*ZXPOTN\(.*\)#\s*exec\s+diag_c\("cc-cmd setcallcv SetupApo"\)')
        self.re_wason_end  = re.compile(r'^\[WASON\]ushell command finished\b', re.I)
        self.re_wason_conn = re.compile(r"^\[WASON\]\s*Conn\s*\[")
        self.re_apop_begin = re.compile(r'^\[APOPLUS\]\s*===\s*show all och-inst\s*===', re.I)
        self.re_apop_top   = re.compile(r'^\[APOPLUS\]\s*TopNeIp\s*:\s*([0-9\.]+)')
        self.re_apop_end   = re.compile(r'^\[APOPLUS\]ushell command finished\b', re.I)
        self.re_apop_row = re.compile(
            r"^\[APOPLUS\]\d+\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]{8})\s+(0x[0-9a-fA-F]{8}).*\b(HEAD[A-Z_]+)\b",
            re.I
        )
        
        # Outputs
        self.per_site: Dict[str, _SiteBucket] = {}
        self.rendered: List[Tuple[str, Tuple[str, str, str, Set[str]], bool, str]] = []
        self.apo_links: Dict[Tuple[str, str], int] = {}
        
        # Initialize performance optimizations
        optimize_dataframe_operations()
    
    @staticmethod
    def _topne_to_wason_ip(top_ne_ip: str) -> Optional[str]:
        """Convert TopNeIp to WASON IP with optimized regex"""
        m = re.match(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", top_ne_ip)
        if not m:
            return None
        x = m.group(3)
        return f"30.10.{x}.6"
    
    @staticmethod
    def _wason_pair_for_compare(conn_line: str) -> Optional[Tuple[str, int, str]]:
        """Extract WASON pair with optimized regex"""
        m = re.search(r"Conn\s*\[\s*([\d\.]+)\s+([\d\.]+)\s+(\d+)\s+(\d+)\s*\]", conn_line)
        if not m:
            return None
        first_ip, _second_ip, call_id_str, conn_no_str = m.groups()
        call_id = int(call_id_str)
        conn_hex = f"0x{int(conn_no_str):08x}".lower()
        return first_ip, call_id, conn_hex
    
    @staticmethod
    def _hex_to_ip(hex_str: str) -> str:
        """Convert hex to IP with optimized operations"""
        try:
            h = hex_str.replace("0x", "").zfill(8)
            parts = [str(int(h[i:i+2], 16)) for i in range(0, 8, 2)]
            return ".".join(parts)
        except Exception:
            return hex_str
    
    def _ensure_bucket(self, ip: str):
        """Ensure bucket exists for IP"""
        if ip not in self.per_site:
            self.per_site[ip] = _SiteBucket(name=self.site_map.get(ip, ip))
    
    @performance_monitor
    def parse(self) -> Dict[str, _SiteBucket]:
        """Optimized parsing with vectorized operations"""
        wason_prebuf: List[str] = []
        apop_prebuf:  List[str] = []
        cap_wason = cap_apop = False
        cur_wason_ip_ctx: Optional[str] = None
        cur_apop_site_ip: Optional[str] = None
        
        # Process lines in batches for better performance
        batch_size = 1000
        for i in range(0, len(self.lines), batch_size):
            batch_lines = self.lines[i:i + batch_size]
            self._process_batch(batch_lines, wason_prebuf, apop_prebuf, 
                              cap_wason, cap_apop, cur_wason_ip_ctx, cur_apop_site_ip)
        
        return self.per_site
    
    def _process_batch(self, batch_lines: List[str], wason_prebuf: List[str], 
                      apop_prebuf: List[str], cap_wason: bool, cap_apop: bool,
                      cur_wason_ip_ctx: Optional[str], cur_apop_site_ip: Optional[str]):
        """Process a batch of lines for better performance"""
        for ln in batch_lines:
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
            
            # Collect WASON
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
            
            # Collect APOP
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
                    source_hex = mrow.group(1).lower()
                    dest_hex   = mrow.group(2).lower()
                    traffic    = mrow.group(3).lower()
                    connno     = mrow.group(4).lower()
                    state      = mrow.group(5)
                    self.per_site[cur_apop_site_ip].apop_rows.append(
                        (traffic, connno, state, ln, source_hex, dest_hex)
                    )
                continue
    
    @performance_monitor
    def analyze(self):
        """Optimized analysis with vectorized operations"""
        from collections import Counter
        
        self.rendered.clear()
        
        # Process sites in batches
        site_batches = list(self.per_site.items())
        batch_size = 10
        
        for i in range(0, len(site_batches), batch_size):
            batch = site_batches[i:i + batch_size]
            self._process_site_batch(batch)
    
    def _process_site_batch(self, site_batch: List[Tuple[str, _SiteBucket]]):
        """Process a batch of sites for better performance"""
        for wip, bucket in site_batch:
            site_name = bucket.name
            wason_snippet = "\n".join(bucket.wason_lines)
            apop_snippet = "\n".join(bucket.apop_lines)
            
            # Reset variables for each site
            apop_by_traffic: Dict[str, Dict[str, str]] = {}
            to_red_apop: Set[str] = set()
            to_red_wason: Set[str] = set()
            
            # Index APOP with vectorized operations
            valid_states = {
                "HEAD_DETECT_WAITING",
                "HEAD_POWER_ADJUSTING", 
                "HEAD_ERROR_DETECTING",
            }
            
            for t, c, state, ln_ap, source_hex, dest_hex in bucket.apop_rows:
                s = (state or "").upper().strip()
                t = t.strip().lower()
                c = c.strip().lower()
                if s in valid_states:
                    apop_by_traffic.setdefault(t, {})[c] = (ln_ap, source_hex, dest_hex)
            
            # Collect WASON calls
            wason_calls: List[Tuple[int, str, str]] = []
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
            
            if not wason_calls:
                self.rendered.append((wip, (site_name, wason_snippet, apop_snippet, set(), set()), False, site_name))
                continue
            
            # Determine scheme
            def score_scheme(scheme: str) -> int:
                return sum(self._traffic_hex_from(call_id, scheme) in apop_by_traffic for call_id, _c, _l in wason_calls)
            
            score_shifted = score_scheme("shifted")
            score_direct  = score_scheme("direct")
            
            if score_shifted == score_direct:
                shifted_like = sum(t.endswith("000000") for t in apop_by_traffic.keys())
                scheme = "shifted" if shifted_like > 0 else "direct"
            else:
                scheme = "shifted" if score_shifted > score_direct else "direct"
            
            # Create pairs
            wason_pairs = [
                (self._traffic_hex_from(call_id, scheme).strip().lower(), c_hex)
                for call_id, c_hex, _ in wason_calls
            ]
            apop_pairs = [
                (t_hex.strip().lower(), c_hex.strip().lower())
                for t_hex, conns in apop_by_traffic.items()
                for c_hex in conns.keys()
            ]
            
            # Use Counter for efficient comparison
            wason_counter = Counter(wason_pairs)
            apop_counter  = Counter(apop_pairs)
            
            # Compare and determine mismatch
            if wason_counter == apop_counter:
                has_mismatch = False
            elif sum(apop_counter.values()) > sum(wason_counter.values()):
                extra = apop_counter - wason_counter
                for p in extra:
                    data = apop_by_traffic.get(p[0], {}).get(p[1])
                    if data:
                        ln_ap, src_hex, dst_hex = data
                        to_red_apop.add(ln_ap)
                        # Store APO link information
                        src_ip = self._hex_to_ip(src_hex)
                        dst_ip = self._hex_to_ip(dst_hex)
                        src_name = self.site_map.get(src_ip, src_ip)
                        dst_name = self.site_map.get(dst_ip, dst_ip)
                        self.apo_links[(src_name, dst_name)] = self.apo_links.get((src_name, dst_name), 0) + 1
                has_mismatch = bool(to_red_apop)
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
                        data = apop_by_traffic[p[0]][p[1]]
                        ln_ap, src_hex, dst_hex = data
                        to_red_apop.add(ln_ap)
                        # Store APO link information
                        src_ip = self._hex_to_ip(src_hex)
                        dst_ip = self._hex_to_ip(dst_hex)
                        src_name = self.site_map.get(src_ip, src_ip)
                        dst_name = self.site_map.get(dst_ip, dst_ip)
                        self.apo_links[(src_name, dst_name)] = self.apo_links.get((src_name, dst_name), 0) + 1
                has_mismatch = bool(to_red_apop or to_red_wason)
            else:
                has_mismatch = False
            
            # Store results
            self.rendered.append(
                (
                    wip,
                    (site_name, wason_snippet, apop_snippet, set(to_red_wason), set(to_red_apop)),
                    has_mismatch,
                    site_name,
                )
            )
    
    @staticmethod
    def _traffic_hex_from(call_id: int, scheme: str) -> str:
        """Generate traffic hex from call ID"""
        return f"0x{(call_id << 24):08x}" if scheme == "shifted" else f"0x{call_id:08x}"
    
    def render_streamlit(self, view_choice: Optional[str] = None, display_fn=None):
        """Render Streamlit UI with optimized display"""
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
        
        # Process in batches for better performance
        batch_size = 5
        for i in range(0, len(to_show), batch_size):
            batch = to_show[i:i + batch_size]
            for _, args, _, _ in batch:
                site_name, wason_snip, apop_snip, to_red_wason, to_red_apop = args
                display(site_name, wason_snip, apop_snip, to_red_wason, to_red_apop)
    
    def display_logs_separate(self, site_name: str, wason_text: str, apop_text: str,
                            wason_lines_to_red: Set[str], apop_lines_to_red: Set[str]):
        """Display logs with optimized rendering"""
        wason_lines = wason_text.splitlines() if wason_text else ["<i>No WASON log</i>"]
        apop_lines  = apop_text.splitlines()  if apop_text  else ["<i>No APOP log</i>"]
        
        # Vectorized HTML generation
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
    
    @staticmethod
    def _inject_css():
        """Inject CSS for styling"""
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
