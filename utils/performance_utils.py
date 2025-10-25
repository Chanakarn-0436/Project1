# utils/performance_utils.py
"""
Performance optimization utilities for Network Monitoring Dashboard
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Union
import warnings
from functools import wraps
import time

def optimize_dataframe_operations():
    """Set pandas options for better performance"""
    pd.set_option('mode.chained_assignment', None)
    pd.set_option('compute.use_bottleneck', True)
    pd.set_option('compute.use_numexpr', True)
    warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)

def vectorized_merge(df1: pd.DataFrame, df2: pd.DataFrame, 
                    left_on: str, right_on: str, 
                    how: str = 'inner') -> pd.DataFrame:
    """
    Optimized merge with pre-filtering and type optimization
    """
    # Pre-filter to reduce merge size
    if len(df1) > 10000:
        # Sample for large datasets if needed
        df1_sample = df1.sample(min(10000, len(df1)))
    else:
        df1_sample = df1
    
    # Ensure consistent dtypes
    if left_on in df1_sample.columns and right_on in df2.columns:
        df1_sample[left_on] = df1_sample[left_on].astype(str)
        df2[right_on] = df2[right_on].astype(str)
    
    return pd.merge(df1_sample, df2, left_on=left_on, right_on=right_on, how=how, validate='one_to_many')

def batch_process_dataframe(df: pd.DataFrame, 
                          batch_size: int = 1000,
                          process_func: callable = None) -> pd.DataFrame:
    """
    Process large DataFrames in batches to avoid memory issues
    """
    if len(df) <= batch_size:
        return process_func(df) if process_func else df
    
    results = []
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size]
        if process_func:
            processed_batch = process_func(batch)
        else:
            processed_batch = batch
        results.append(processed_batch)
    
    return pd.concat(results, ignore_index=True)

def fast_string_operations(df: pd.DataFrame, 
                          columns: List[str],
                          operations: Dict[str, str]) -> pd.DataFrame:
    """
    Optimized string operations using vectorized methods
    """
    df_result = df.copy()
    
    for col in columns:
        if col in df_result.columns:
            if 'strip' in operations:
                df_result[col] = df_result[col].astype(str).str.strip()
            if 'lower' in operations:
                df_result[col] = df_result[col].str.lower()
            if 'upper' in operations:
                df_result[col] = df_result[col].str.upper()
    
    return df_result

def optimized_groupby_apply(df: pd.DataFrame, 
                           group_cols: List[str],
                           agg_dict: Dict[str, str]) -> pd.DataFrame:
    """
    Optimized groupby operations using agg instead of apply
    """
    return df.groupby(group_cols).agg(agg_dict).reset_index()

def memory_efficient_concat(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Memory-efficient concatenation of DataFrames
    """
    if not dataframes:
        return pd.DataFrame()
    
    # Filter out empty DataFrames
    non_empty_dfs = [df for df in dataframes if not df.empty]
    
    if not non_empty_dfs:
        return pd.DataFrame()
    
    if len(non_empty_dfs) == 1:
        return non_empty_dfs[0]
    
    return pd.concat(non_empty_dfs, ignore_index=True, sort=False)

def cache_expensive_operations(func):
    """
    Decorator to cache expensive operations
    """
    cache = {}
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Create cache key from function name and arguments
        cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
        
        if cache_key in cache:
            return cache[cache_key]
        
        result = func(*args, **kwargs)
        cache[cache_key] = result
        return result
    
    return wrapper

def optimize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimize numeric columns by downcasting to appropriate dtypes
    """
    df_optimized = df.copy()
    
    for col in df_optimized.columns:
        if df_optimized[col].dtype == 'object':
            # Try to convert to numeric
            try:
                df_optimized[col] = pd.to_numeric(df_optimized[col], errors='ignore')
            except (ValueError, TypeError):
                pass
        
        if df_optimized[col].dtype in ['int64', 'int32']:
            # Downcast integers
            df_optimized[col] = pd.to_numeric(df_optimized[col], downcast='integer')
        elif df_optimized[col].dtype in ['float64', 'float32']:
            # Downcast floats
            df_optimized[col] = pd.to_numeric(df_optimized[col], downcast='float')
    
    return df_optimized

def fast_filter_operations(df: pd.DataFrame, 
                          filters: Dict[str, Any]) -> pd.DataFrame:
    """
    Optimized filtering using vectorized operations
    """
    mask = pd.Series(True, index=df.index)
    
    for col, condition in filters.items():
        if col in df.columns:
            if isinstance(condition, dict):
                if 'min' in condition:
                    mask &= (df[col] >= condition['min'])
                if 'max' in condition:
                    mask &= (df[col] <= condition['max'])
                if 'eq' in condition:
                    mask &= (df[col] == condition['eq'])
                if 'in' in condition:
                    mask &= df[col].isin(condition['in'])
            else:
                mask &= (df[col] == condition)
    
    return df[mask]

def performance_monitor(func):
    """
    Decorator to monitor function performance
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        print(f"Function {func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    
    return wrapper

def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimize DataFrame memory usage
    """
    df_optimized = df.copy()
    
    for col in df_optimized.columns:
        col_type = df_optimized[col].dtype
        
        if col_type != 'object':
            c_min = df_optimized[col].min()
            c_max = df_optimized[col].max()
            
            if str(col_type).startswith('int'):
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df_optimized[col] = df_optimized[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df_optimized[col] = df_optimized[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df_optimized[col] = df_optimized[col].astype(np.int32)
            else:
                if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                    df_optimized[col] = df_optimized[col].astype(np.float16)
                elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df_optimized[col] = df_optimized[col].astype(np.float32)
    
    return df_optimized

# Initialize performance optimizations
optimize_dataframe_operations()
