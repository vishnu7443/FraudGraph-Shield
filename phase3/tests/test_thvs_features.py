import numpy as np
import pandas as pd
from thvs import compute_thvs, compute_retention_ratio

def create_mock_account(credit_vel=0.5, debit_vel=0.5, short_vel=None, long_vel=None, all_vel=None):
    """
    Helper to create a mock row dictionary for THVS tests.
    """
    row = {}
    
    # 1-week, 1-month, 3-month lookback columns mock
    # Credit cols: index % 6 in [1, 3, 5]
    # Debit cols: index % 6 in [2, 4, 0]
    # Short window: % 6 in [1, 2]
    # Long window: % 6 in [5, 0]
    
    credit_cols = ['F1', 'F3', 'F5']
    debit_cols = ['F2', 'F4', 'F6']
    
    if all_vel is not None:
        for c in credit_cols + debit_cols:
            row[c] = all_vel
    else:
        for c in credit_cols:
            row[c] = credit_vel
        for c in debit_cols:
            row[c] = debit_vel
            
    if short_vel is not None:
        row['F1'] = short_vel
        row['F2'] = short_vel
    if long_vel is not None:
        row['F5'] = long_vel
        row['F6'] = long_vel
        
    return row

def test_mule_like_account_has_low_retention():
    # Account with equal credit and debit velocity should have ~0 retention
    mock_row = create_mock_account(credit_vel=1.0, debit_vel=0.98)
    credit_cols = ['F1', 'F3', 'F5']
    debit_cols = ['F2', 'F4', 'F6']
    retention = compute_retention_ratio(credit_cols, debit_cols, mock_row)
    assert retention < 0.10

def test_normal_account_has_high_retention():
    mock_row = create_mock_account(credit_vel=0.5, debit_vel=0.1)
    credit_cols = ['F1', 'F3', 'F5']
    debit_cols = ['F2', 'F4', 'F6']
    retention = compute_retention_ratio(credit_cols, debit_cols, mock_row)
    assert retention > 0.70

def test_thvs_hop_speed_high_for_burst_accounts():
    # short-window activity (F1, F2) far exceeds long-window (F5, F6)
    mock_row = create_mock_account(short_vel=2.0, long_vel=0.4)
    short_window_cols = ['F1', 'F2']
    long_window_cols = ['F5', 'F6']
    hop_speed = compute_thvs(mock_row, short_window_cols, long_window_cols)
    assert hop_speed > 3.0

def test_thvs_returns_finite_values():
    # Test edge case: all velocity features are 0.5 (neutral)
    mock_row = create_mock_account(all_vel=0.5)
    short_window_cols = ['F1', 'F2']
    long_window_cols = ['F5', 'F6']
    hop_speed = compute_thvs(mock_row, short_window_cols, long_window_cols)
    assert np.isfinite(hop_speed)
