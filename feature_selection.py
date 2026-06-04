# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import lightgbm as lgb
from preprocessor import FraudPreprocessor

def run_round_1_filter(df_raw, target_col='F3897'):
    """
    Round 1 — quick dirty filter:
    Remove any column with more than 95% NA in the raw data.
    Remove any column with zero variance (constant columns) in the raw data.
    """
    print("Starting Feature Selection: Round 1 (Filter)...")
    initial_cols = list(df_raw.columns)
    
    # Exclude target and index columns from the filtering
    exclude_cols = [target_col, 'Unnamed: 0']
    cols_to_check = [c for c in initial_cols if c not in exclude_cols]
    
    # 1. Remove columns with >95% NA
    na_pct = df_raw[cols_to_check].isna().mean()
    high_na_cols = list(na_pct[na_pct > 0.95].index)
    print(f"  Found {len(high_na_cols)} columns with > 95% NA values.")
    
    # 2. Remove columns with zero variance (constant columns)
    # We check the number of unique non-NA values. If <= 1, the column has zero variance.
    constant_cols = []
    for col in cols_to_check:
        if col in high_na_cols:
            continue
        try:
            # We drop NA values to check unique count
            unique_count = df_raw[col].dropna().nunique()
            if unique_count <= 1:
                constant_cols.append(col)
        except Exception:
            # If any error happens, assume it might be problematic and keep it or drop it.
            # Safety fallback: do not drop if we are unsure.
            pass
    print(f"  Found {len(constant_cols)} constant or all-NA columns.")
    
    cols_to_drop = list(set(high_na_cols + constant_cols))
    selected_cols_r1 = [c for c in initial_cols if c not in cols_to_drop]
    
    print(f"  Round 1 filtered out {len(cols_to_drop)} columns. Remaining: {len(selected_cols_r1)}")
    return selected_cols_r1, cols_to_drop


def run_round_2_lgb_importance(X_train, y_train, top_n=300):
    """
    Round 2 — LightGBM built-in importance:
    Train a fast LightGBM model with 100 estimators on the full remaining feature set with no tuning.
    Extract feature_importances_. Keep the top 300 features by importance score.
    """
    print(f"Starting Feature Selection: Round 2 (LightGBM Importance, selecting top {top_n})...")
    
    # Train a fast LightGBM model
    model = lgb.LGBMClassifier(
        n_estimators=100,
        random_state=42,
        verbose=-1,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Extract importances
    importances = model.feature_importances_
    feature_names = X_train.columns
    
    # Create DataFrame of feature importances
    imp_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    }).sort_values(by='importance', ascending=False)
    
    # Keep top N features
    top_features = list(imp_df['feature'].head(top_n).values)
    print(f"  Selected top {len(top_features)} features.")
    print("  Top 10 features by LightGBM importance:")
    for idx, row in imp_df.head(10).iterrows():
        print(f"    - {row['feature']}: {row['importance']}")
        
    return top_features, imp_df
