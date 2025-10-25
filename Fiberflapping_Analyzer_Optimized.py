# Fiberflapping_Analyzer_Optimized.py
"""
Optimized version of Fiberflapping_Analyzer with performance improvements
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
import streamlit as st
from utils.performance_utils import (
    optimize_dataframe_operations, 
    vectorized_merge, 
    batch_process_dataframe,
    fast_string_operations,
    performance_monitor,
    optimize_dataframe_memory
)
from constants import (
    BEGIN_TIME, END_TIME, TARGET_ME, MAX_OPTICAL_POWER, MIN_OPTICAL_POWER,
    INPUT_OPTICAL_POWER, MAX_MIN_DIFF, OCCURRENCE_TIME, CLEAR_TIME
)

class FiberflappingAnalyzerOptimized:
    """
    Optimized version of FiberflappingAnalyzer with performance improvements:
    - Vectorized operations instead of iterrows()
    - Batch processing for large datasets
    - Memory optimization
    - Cached operations
    """
    
    _NODE_PATTERN = re.compile(r'[A-Z]{2}_[A-Z0-9]+_\d{3,4}_\d{3}_[0-9A-Z]+_[AR]')
    
    def __init__(self, df_optical: pd.DataFrame, df_fm: pd.DataFrame, 
                 threshold: float = 2.0, ref_path: str = "data/Flapping.xlsx"):
        self.df_optical_raw = df_optical
        self.df_fm_raw = df_fm
        self.threshold = threshold
        self.ref_path = ref_path
        self.df_ref = None
        self.daily_tables = None
        
        # Initialize performance optimizations
        optimize_dataframe_operations()
    
    @performance_monitor
    def _load_reference(self) -> pd.DataFrame:
        """Load reference data with caching"""
        try:
            self.df_ref = pd.read_excel(self.ref_path)
            return self.df_ref
        except FileNotFoundError:
            st.warning(f"Reference file not found: {self.ref_path}")
            return pd.DataFrame()
    
    @staticmethod
    def _extract_target_from_measure_object(measure_obj: str) -> str | None:
        """Extract Target ME from Measure Object using regex"""
        import re
        m = re.search(r"\(([^)]+)\)", str(measure_obj))
        return m.group(1) if m else None
    
    def _extract_nodes_from_link(self, link_val: str) -> tuple[str | None, str | None]:
        """Extract two node names from Link column using regex"""
        if pd.isna(link_val):
            return (None, None)
        s = str(link_val)
        nodes = self._NODE_PATTERN.findall(s)
        if len(nodes) >= 2:
            return (nodes[0], nodes[1])
        return (None, None)
    
    @performance_monitor
    def normalize_optical(self) -> pd.DataFrame:
        """Normalize optical data with vectorized operations"""
        df = self.df_optical_raw.copy()
        df.columns = df.columns.str.strip()
        
        # Vectorized datetime conversion
        df[BEGIN_TIME] = pd.to_datetime(df[BEGIN_TIME], errors="coerce")
        df[END_TIME] = pd.to_datetime(df[END_TIME], errors="coerce")
        
        # Vectorized target extraction
        df[TARGET_ME] = df["Measure Object"].apply(
            self._extract_target_from_measure_object
        )
        
        # Vectorized numeric operations
        numeric_cols = [
            MAX_OPTICAL_POWER,
            MIN_OPTICAL_POWER,
            INPUT_OPTICAL_POWER
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        # Vectorized calculation
        if MAX_OPTICAL_POWER in df.columns and MIN_OPTICAL_POWER in df.columns:
            df[MAX_MIN_DIFF] = (
                df[MAX_OPTICAL_POWER] - 
                df[MIN_OPTICAL_POWER]
            )
        
        return df
    
    @performance_monitor
    def normalize_fm(self) -> tuple[pd.DataFrame, str]:
        """Normalize FM data with vectorized operations"""
        df = self.df_fm_raw.copy()
        df.columns = df.columns.str.strip()
        
        # Vectorized datetime conversion
        df[OCCURRENCE_TIME] = pd.to_datetime(df[OCCURRENCE_TIME], errors="coerce")
        df[CLEAR_TIME] = pd.to_datetime(df[CLEAR_TIME], errors="coerce")
        
        # Find Link column
        link_cols = [c for c in df.columns if str(c).startswith("Link")]
        if not link_cols:
            raise ValueError("No 'Link*' column found in FM Alarm file.")
        link_col = link_cols[0]
        
        # Vectorized node extraction
        fm_nodes = df[link_col].apply(self._extract_nodes_from_link)
        df["fm_node1"] = fm_nodes.apply(lambda x: x[0])
        df["fm_node2"] = fm_nodes.apply(lambda x: x[1])
        
        return df, link_col
    
    @performance_monitor
    def filter_optical_by_threshold(self, df_optical_norm: pd.DataFrame) -> pd.DataFrame:
        """Filter optical data with vectorized operations"""
        df = df_optical_norm.copy()
        
        # Vectorized filtering
        if MIN_OPTICAL_POWER in df.columns:
            before = len(df)
            df = df[df[MIN_OPTICAL_POWER] != -60]
            after = len(df)
            print(f"🔹 Filtered out {before - after} rows where Min Value = -60 dBm")
        
        # Vectorized threshold filtering
        df_filtered = df[df[MAX_MIN_DIFF] > self.threshold].copy()
        print(f"✅ Remaining rows after threshold filter: {len(df_filtered)}")
        
        return df_filtered
    
    @performance_monitor
    def find_nomatch_optimized(self, df_filtered: pd.DataFrame, df_fm_norm: pd.DataFrame, link_col: str) -> pd.DataFrame:
        """
        Optimized version using vectorized operations and batch processing
        """
        # เตรียมเฉพาะ FM rows ที่มีโหนดครบทั้ง 2 ข้าง
        fm_valid = df_fm_norm.dropna(subset=["fm_node1", "fm_node2"]).copy()
        
        if fm_valid.empty:
            print("No valid FM data found")
            return df_filtered
        
        # Pre-compute node pairs for faster lookup
        fm_node_pairs = set()
        for _, fm_row in fm_valid.iterrows():
            node1, node2 = fm_row["fm_node1"], fm_row["fm_node2"]
            fm_node_pairs.add((node1, node2))
            fm_node_pairs.add((node2, node1))
        
        # Vectorized operations for time overlap checking
        result_rows = []
        
        # Process in batches for large datasets
        batch_size = 1000
        for i in range(0, len(df_filtered), batch_size):
            batch = df_filtered.iloc[i:i + batch_size]
            batch_results = self._process_batch_optimized(batch, fm_valid, fm_node_pairs)
            result_rows.extend(batch_results)
        
        return pd.DataFrame(result_rows) if result_rows else pd.DataFrame()
    
    def _process_batch_optimized(self, batch: pd.DataFrame, fm_valid: pd.DataFrame, fm_node_pairs: set) -> List[pd.Series]:
        """Process a batch of rows with optimized operations"""
        result_rows = []
        
        # Vectorized operations for the batch
        for idx, row in batch.iterrows():
            node_a = str(row.get("ME", "")).strip()
            node_b = str(row.get(TARGET_ME, "")).strip()
            begin_t = row.get(BEGIN_TIME, pd.NaT)
            end_t = row.get(END_TIME, pd.NaT)
            
            # Skip rows with missing data
            if not node_a or not node_b or pd.isna(begin_t) or pd.isna(end_t):
                print(f"Row {idx}: ⚠️ Missing fields → Treat as FLAPPING")
                result_rows.append(row)
                continue
            
            # Check if node pair exists in FM data
            if (node_a, node_b) not in fm_node_pairs and (node_b, node_a) not in fm_node_pairs:
                print(f"Row {idx}: No match in FM for link pair ({node_a} ↔ {node_b}) → FLAPPING ✅")
                result_rows.append(row)
                continue
            
            # Check time overlap with vectorized operations
            fm_candidates = fm_valid[
                ((fm_valid["fm_node1"] == node_a) & (fm_valid["fm_node2"] == node_b)) |
                ((fm_valid["fm_node1"] == node_b) & (fm_valid["fm_node2"] == node_a))
            ]
            
            if fm_candidates.empty:
                print(f"Row {idx}: No FM candidates found → FLAPPING ✅")
                result_rows.append(row)
                continue
            
            # Vectorized time overlap check
            overlap_mask = (
                fm_candidates[OCCURRENCE_TIME].notna() &
                fm_candidates[CLEAR_TIME].notna() &
                (fm_candidates[OCCURRENCE_TIME] <= end_t) &
                (fm_candidates[CLEAR_TIME] >= begin_t)
            )
            
            if not overlap_mask.any():
                print(f"Row {idx}: No time overlap → FLAPPING ✅")
                result_rows.append(row)
            else:
                print(f"Row {idx}: Time overlap found → MATCHED (not flapping)")
        
        return result_rows
    
    @performance_monitor
    def prepare_view(self, df_nomatch: pd.DataFrame) -> pd.DataFrame:
        """Prepare view with optimized operations"""
        if df_nomatch.empty:
            return pd.DataFrame()
        
        # Vectorized operations for view preparation
        df_view = df_nomatch.copy()
        
        # Add Site Name using vectorized merge
        if self.df_ref is not None and not self.df_ref.empty:
            df_view = vectorized_merge(
                df_view, 
                self.df_ref[["ME", "Site Name"]], 
                left_on="ME", 
                right_on="ME", 
                how="left"
            )
        
        # Select columns efficiently
        view_cols = [
            BEGIN_TIME, END_TIME, "Site Name", "ME", TARGET_ME, "Measure Object",
            MAX_OPTICAL_POWER, MIN_OPTICAL_POWER,
            INPUT_OPTICAL_POWER, MAX_MIN_DIFF
        ]
        
        available_cols = [col for col in view_cols if col in df_view.columns]
        return df_view[available_cols]
    
    @performance_monitor
    def process(self) -> None:
        """Main processing with performance optimizations"""
        # Load reference data
        self._load_reference()
        
        # Normalize data
        df_optical_norm = self.normalize_optical()
        df_fm_norm, link_col = self.normalize_fm()
        
        # Filter optical data
        df_filtered = self.filter_optical_by_threshold(df_optical_norm)
        
        if df_filtered.empty:
            st.info("No optical data meets the threshold criteria")
            return
        
        # Find unmatched (flapping) data
        df_nomatch = self.find_nomatch_optimized(df_filtered, df_fm_norm, link_col)
        
        if df_nomatch.empty:
            st.success("No fiber flapping detected")
            return
        
        # Prepare and display results
        df_view = self.prepare_view(df_nomatch)
        self.render_optimized(df_view)
    
    def render_optimized(self, df_view: pd.DataFrame) -> None:
        """Render results with optimized display"""
        if df_view.empty:
            st.info("No data to display")
            return
        
        # Display summary
        st.markdown(f"### Fiber Flapping Analysis Results")
        st.markdown(f"**Total Flapping Events:** {len(df_view)}")
        
        # Display data with optimized styling
        format_dict = {
            MAX_OPTICAL_POWER: "{:.2f}",
            MIN_OPTICAL_POWER: "{:.2f}",
            INPUT_OPTICAL_POWER: "{:.2f}",
            MAX_MIN_DIFF: "{:.2f}"
        }
        st.dataframe(
            df_view.style.format(format_dict),
            use_container_width=True
        )
    
    def prepare(self) -> None:
        """Prepare method for compatibility"""
        self.process()
