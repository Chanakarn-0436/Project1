# Line_Analyzer_Optimized.py
"""
Optimized version of Line_Analyzer with performance improvements
"""
import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, List, Tuple, Optional
from utils.performance_utils import (
    optimize_dataframe_operations,
    vectorized_merge,
    batch_process_dataframe,
    fast_string_operations,
    performance_monitor,
    optimize_dataframe_memory,
    optimized_groupby_apply
)

class Line_Analyzer_Optimized:
    """
    Optimized version of Line_Analyzer with performance improvements:
    - Vectorized operations instead of iterrows()
    - Optimized groupby operations
    - Memory-efficient processing
    - Batch processing for large datasets
    """
    
    def __init__(self, df_line: pd.DataFrame, df_ref: pd.DataFrame, 
                 pmap: dict | None = None, ns: str = "line"):
        self.df_line = df_line
        self.df_ref = df_ref
        self.pmap = pmap or {}
        self.ns = ns
        
        # Initialize performance optimizations
        optimize_dataframe_operations()
    
    @staticmethod
    def get_preset_map(log_text: str) -> dict:
        """Extract preset mapping from log text with optimized regex"""
        import re
        pmap = {}
        
        # Optimized regex pattern
        pattern = r'Preset\s*(\d+)\s*:\s*(\d+)'
        matches = re.findall(pattern, log_text)
        
        for preset, call_id in matches:
            pmap[int(call_id)] = int(preset)
        
        return pmap
    
    @performance_monitor
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize columns with vectorized operations"""
        df_norm = df.copy()
        df_norm.columns = fast_string_operations(
            pd.DataFrame(df_norm.columns.reshape(-1, 1)), 
            [0], 
            {'strip': True, 'lower': False}
        )[0].values
        
        return df_norm
    
    @performance_monitor
    def _merge_with_ref(self) -> pd.DataFrame:
        """Optimized merge with reference data"""
        # Vectorized operations for mapping format
        df_line_norm = self._normalize_columns(self.df_line)
        df_ref_norm = self._normalize_columns(self.df_ref)
        
        # Vectorized mapping format creation
        df_line_norm["Mapping Format"] = (
            df_line_norm["ME"].astype(str).str.strip() + 
            df_line_norm["Measure Object"].astype(str).str.strip()
        )
        df_ref_norm["Mapping"] = df_ref_norm["Mapping"].astype(str).str.strip()
        
        # Optimized merge
        merged = vectorized_merge(
            df_line_norm, 
            df_ref_norm, 
            left_on="Mapping Format", 
            right_on="Mapping", 
            how="inner"
        )
        
        return merged
    
    @performance_monitor
    def _apply_preset_route(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply preset route with vectorized operations"""
        if not self.pmap:
            return df
        
        # Vectorized preset mapping
        df["PresetNo"] = df["Call ID"].map(self.pmap)
        df["Route"] = df.apply(
            lambda row: f"Preset {row['PresetNo']}" if pd.notna(row['PresetNo']) else row.get('Route', ''),
            axis=1
        )
        
        return df
    
    @performance_monitor
    def _row_has_issue_vectorized(self, df: pd.DataFrame) -> pd.Series:
        """Vectorized version of row issue detection"""
        # Vectorized numeric conversions
        ber = pd.to_numeric(df.get("Instant BER After FEC", 0), errors="coerce")
        thr = pd.to_numeric(df.get("Threshold", 0), errors="coerce")
        
        out_val = pd.to_numeric(df.get("Output Optical Power (dBm)", 0), errors="coerce")
        out_max = pd.to_numeric(df.get("Maximum threshold(out)", 0), errors="coerce")
        out_min = pd.to_numeric(df.get("Minimum threshold(out)", 0), errors="coerce")
        
        in_val = pd.to_numeric(df.get("Input Optical Power(dBm)", 0), errors="coerce")
        in_max = pd.to_numeric(df.get("Maximum threshold(in)", 0), errors="coerce")
        in_min = pd.to_numeric(df.get("Minimum threshold(in)", 0), errors="coerce")
        
        # Vectorized condition checks
        ber_issue = (ber.notna() & thr.notna() & (ber > thr))
        out_issue = (out_val.notna() & out_max.notna() & out_min.notna() & 
                    ((out_val < out_min) | (out_val > out_max)))
        in_issue = (in_val.notna() & in_max.notna() & in_min.notna() & 
                   ((in_val < in_min) | (in_val > in_max)))
        
        return ber_issue | out_issue | in_issue
    
    @performance_monitor
    def _style_dataframe_optimized(self, df_view: pd.DataFrame) -> pd.DataFrame:
        """Optimized dataframe styling"""
        # Convert numeric columns
        numeric_cols = [
            "Instant BER After FEC", "Threshold",
            "Output Optical Power (dBm)", "Input Optical Power(dBm)",
            "Maximum threshold(out)", "Minimum threshold(out)",
            "Maximum threshold(in)", "Minimum threshold(in)"
        ]
        
        for col in numeric_cols:
            if col in df_view.columns:
                df_view[col] = pd.to_numeric(df_view[col], errors="coerce")
        
        # Vectorized issue detection
        issue_mask = self._row_has_issue_vectorized(df_view)
        
        # Apply styling
        styled_df = df_view.copy()
        styled_df['_has_issue'] = issue_mask
        
        return styled_df
    
    @performance_monitor
    def _render_summary_kpi_optimized(self, df_view: pd.DataFrame) -> None:
        """Optimized summary KPI rendering"""
        # Vectorized calculations
        total = len(df_view)
        
        # Vectorized issue detection
        issue_mask = self._row_has_issue_vectorized(df_view)
        abnormal_count = issue_mask.sum()
        
        # Display metrics
        cols = st.columns(4)
        with cols[0]:
            st.metric("Total Lines", f"{total}")
        with cols[1]:
            st.metric("Normal Lines", f"{total - abnormal_count}")
        with cols[2]:
            st.metric("Abnormal Lines", f"{abnormal_count}")
        with cols[3]:
            # Preset usage from session state
            preset_analyzer = st.session_state.get("preset_analyzer")
            if preset_analyzer:
                _, summary = preset_analyzer.to_dataframe()
                preset_used = int(summary.get("total", 0))
                preset_fail = int(summary.get("fails", 0))
                st.metric("Preset Usage", f"{preset_used}", f"{preset_fail} Fail")
            else:
                st.metric("Preset Usage", "N/A")
    
    @performance_monitor
    def _render_problem_call_ids_optimized(self, df_view: pd.DataFrame) -> None:
        """Optimized problem call IDs rendering"""
        # Vectorized issue detection
        issue_mask = self._row_has_issue_vectorized(df_view)
        
        if not issue_mask.any():
            st.info("No abnormal lines found")
            return
        
        # Filter abnormal rows
        abnormal_df = df_view[issue_mask].copy()
        
        # Convert numeric columns for display
        numeric_cols = [
            "Instant BER After FEC", "Threshold",
            "Output Optical Power (dBm)", "Input Optical Power(dBm)"
        ]
        
        for col in numeric_cols:
            if col in abnormal_df.columns:
                abnormal_df[col] = pd.to_numeric(abnormal_df[col], errors="coerce")
        
        # Display results
        st.markdown(f"#### Problem Call IDs (BER/Input/Output abnormal) - Found {len(abnormal_df)} rows")
        
        # Select columns to display
        display_cols = [
            "Site Name", "ME", "Call ID", "Measure Object",
            "Instant BER After FEC", "Threshold",
            "Output Optical Power (dBm)", "Input Optical Power(dBm)"
        ]
        
        available_cols = [col for col in display_cols if col in abnormal_df.columns]
        st.dataframe(abnormal_df[available_cols], use_container_width=True)
    
    @performance_monitor
    def _render_preset_kpi_optimized(self, df_view: pd.DataFrame) -> None:
        """Optimized preset KPI rendering"""
        # Filter preset data
        preset_mask = df_view.get("Route", pd.Series([], dtype=object)).astype(str).str.startswith("Preset")
        preset_df = df_view[preset_mask].copy()
        
        if preset_df.empty:
            st.info("No preset data found")
            return
        
        # Vectorized preset analysis
        preset_df["PresetNo"] = preset_df["Route"].astype(str).str.extract(r"Preset\s*(\d+)")
        
        # Vectorized issue detection for presets
        issue_mask = self._row_has_issue_vectorized(preset_df)
        preset_df["IsAbnormal"] = issue_mask
        
        # Groupby operations
        preset_summary = optimized_groupby_apply(
            preset_df,
            ["PresetNo"],
            {"IsAbnormal": "any", "PresetNo": "count"}
        )
        
        preset_summary["Status"] = preset_summary["IsAbnormal"].map(
            lambda x: "Abnormal" if x else "Normal"
        )
        
        # Display results
        st.markdown("#### Preset Usage • Status")
        st.dataframe(preset_summary, use_container_width=True)
    
    @performance_monitor
    def process(self) -> None:
        """Main processing with performance optimizations"""
        # Normalize and merge data
        merged = self._merge_with_ref()
        
        if merged.empty:
            st.error("No data after merging with reference")
            return
        
        # Apply preset route
        merged = self._apply_preset_route(merged)
        
        # Optimize memory usage
        merged = optimize_dataframe_memory(merged)
        
        # Render components
        self._render_summary_kpi_optimized(merged)
        self._render_problem_call_ids_optimized(merged)
        self._render_preset_kpi_optimized(merged)
        
        # Store results for summary table
        st.session_state["line_analyzer"] = self
    
    def prepare(self) -> None:
        """Prepare method for compatibility"""
        self.process()
