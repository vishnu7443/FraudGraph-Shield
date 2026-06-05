import numpy as np
import pandas as pd

def compute_thvs(row, short_window_cols, long_window_cols):
    """
    Computes the Temporal Hop Velocity Signature (THVS) hop speed ratio for a single row/account.
    Excludes neutral imputed values (0.5).
    """
    short_vals = []
    for c in short_window_cols:
        if c in row and row[c] != 0.5 and not pd.isna(row[c]):
            try:
                val = float(row[c])
                short_vals.append(val)
            except (ValueError, TypeError):
                pass
                
    long_vals = []
    for c in long_window_cols:
        if c in row and row[c] != 0.5 and not pd.isna(row[c]):
            try:
                val = float(row[c])
                long_vals.append(val)
            except (ValueError, TypeError):
                pass
                
    short_vel = np.mean(short_vals) if short_vals else 0.5
    long_vel = np.mean(long_vals) if long_vals else 0.5
    
    hop_speed_ratio = short_vel / (long_vel + 1e-8)
    if not np.isfinite(hop_speed_ratio):
        return 1.0
    return hop_speed_ratio

def compute_retention_ratio(credit_velocity_cols, debit_velocity_cols, row):
    """
    Computes the Amount Retention Ratio for a single row/account.
    """
    credit_vals = []
    for c in credit_velocity_cols:
        if c in row and not pd.isna(row[c]):
            try:
                val = float(row[c])
                credit_vals.append(val)
            except (ValueError, TypeError):
                pass
                
    debit_vals = []
    for c in debit_velocity_cols:
        if c in row and not pd.isna(row[c]):
            try:
                val = float(row[c])
                debit_vals.append(val)
            except (ValueError, TypeError):
                pass
                
    avg_credit = np.mean(credit_vals) if credit_vals else 0.5
    avg_debit = np.mean(debit_vals) if debit_vals else 0.5
    
    retention = 1.0 - (avg_debit / (avg_credit + 1e-8))
    return np.clip(retention, 0.0, 1.0)

def compute_thvs_features_df(df):
    """
    Vectorized computation of THVS features for a DataFrame to optimize training performance.
    """
    available_cols = set(df.columns)
    
    # 6-column blocks mapping
    short_window_cols = [f'F{i}' for i in range(1, 3886) if i % 6 in [1, 2] and f'F{i}' in available_cols]
    long_window_cols = [f'F{i}' for i in range(1, 3886) if i % 6 in [5, 0] and f'F{i}' in available_cols]
    
    credit_cols = [f'F{i}' for i in range(1, 3886) if i % 6 in [1, 3, 5] and f'F{i}' in available_cols]
    debit_cols = [f'F{i}' for i in range(1, 3886) if i % 6 in [2, 4, 0] and f'F{i}' in available_cols]
    
    # Convert all columns to numeric, replacing strings with NaN
    all_target_cols = list(set(short_window_cols + long_window_cols + credit_cols + debit_cols))
    df_numeric = df[all_target_cols].apply(pd.to_numeric, errors='coerce')
    
    # Vectorized hop speed ratio
    if short_window_cols:
        short_df = df_numeric[short_window_cols].replace(0.5, np.nan)
        short_mean = short_df.mean(axis=1).fillna(0.5).values
    else:
        short_mean = np.full(len(df), 0.5)
        
    if long_window_cols:
        long_df = df_numeric[long_window_cols].replace(0.5, np.nan)
        long_mean = long_df.mean(axis=1).fillna(0.5).values
    else:
        long_mean = np.full(len(df), 0.5)
        
    hop_speed_ratios = short_mean / (long_mean + 1e-8)
    hop_speed_ratios = np.where(np.isfinite(hop_speed_ratios), hop_speed_ratios, 1.0)
    
    # Vectorized retention ratio
    if credit_cols:
        credit_mean = df_numeric[credit_cols].fillna(0.5).mean(axis=1).values
    else:
        credit_mean = np.full(len(df), 0.5)
        
    if debit_cols:
        debit_mean = df_numeric[debit_cols].fillna(0.5).mean(axis=1).values
    else:
        debit_mean = np.full(len(df), 0.5)
        
    retention_ratios = 1.0 - (debit_mean / (credit_mean + 1e-8))
    retention_ratios = np.clip(retention_ratios, 0.0, 1.0)
    
    return hop_speed_ratios, retention_ratios
