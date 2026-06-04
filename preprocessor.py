import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import joblib
import os

class FraudPreprocessor:
    def __init__(self):
        self.missingness_cols = []
        self.f3886_encoding = {}
        self.f3891_encoding = {}
        self.global_target_mean = 0.2311  # Default fallback based on training data
        self.fitted = False
        
        # Column names
        self.target_col = 'F3897'
        self.velocity_cols = [f'F{i}' for i in range(1, 3886)]
        self.metadata_cols = [f'F{i}' for i in range(3886, 3925) if f'F{i}' != 'F3897']
        self.complexity_cols = [f'F{i}' for i in range(3900, 3925)]
        self.peer_dev_cols = [f'F{i}' for i in range(3880, 3886)]
        self.feature_names_ = []

    def fit_transform(self, df, columns_to_keep=None):
        # 1. Separate features from target. Extract F3897 as y, binarize it. Drop F3897 from features.
        df_copy = df.copy()
        if self.target_col in df_copy.columns:
            y = (df_copy[self.target_col] > 0).astype(int)
            df_copy = df_copy.drop(columns=[self.target_col])
        else:
            y = None
        
        # Keep row indices if there is a column for it (like Unnamed: 0)
        index_col = 'Unnamed: 0'
        if index_col in df_copy.columns:
            df_copy = df_copy.drop(columns=[index_col])
            
        self.global_target_mean = y.mean() if y is not None else 0.2311
        
        # Determine needed raw columns if columns_to_keep is specified
        if columns_to_keep is not None:
            needed_raw_cols = set()
            for col in columns_to_keep:
                if col.endswith('_missing'):
                    base_col = col[:-8]
                    needed_raw_cols.add(base_col)
                elif col == 'product_complexity':
                    needed_raw_cols.update(self.complexity_cols)
                elif col == 'peer_deviation_composite':
                    needed_raw_cols.update(self.peer_dev_cols)
                elif col == 'tenure_days':
                    needed_raw_cols.add('F3888')
                else:
                    needed_raw_cols.add(col)
            # Only keep columns in df_copy that are in needed_raw_cols
            cols_present = [c for c in df_copy.columns if c in needed_raw_cols]
            df_copy = df_copy[cols_present]
            
        # 3. For velocity ratio features (F1–F3885): replace all NA with 0.5.
        existing_velocity_cols = [c for c in self.velocity_cols if c in df_copy.columns]
        for col in existing_velocity_cols:
            df_copy[col] = df_copy[col].fillna(0.5)
            
        # 4. Create missingness indicator vector for columns with >5% NA.
        cols_to_check = [c for c in df_copy.columns if c not in [index_col, self.target_col]]
        
        # Calculate NA percentages
        na_pcts = {col: df_copy[col].isna().mean() for col in cols_to_check}
        self.missingness_cols = [col for col, pct in na_pcts.items() if pct > 0.05]
        
        if columns_to_keep is not None:
            required_missing_bases = [c[:-8] for c in columns_to_keep if c.endswith('_missing')]
            # Only add if the base column exists in the input
            required_missing_bases = [b for b in required_missing_bases if b in df_copy.columns]
            self.missingness_cols = list(set(self.missingness_cols).union(required_missing_bases))
            
        if self.missingness_cols:
            df_dict = {col: df_copy[col].values for col in df_copy.columns}
            for col in self.missingness_cols:
                # check from original raw df to preserve NaNs if they were filled in df_copy
                df_dict[f"{col}_missing"] = df[col].isna().astype(np.int8).values
            df_copy = pd.DataFrame(df_dict, index=df_copy.index)
            del df_dict
            import gc; gc.collect()
            
        # 5. Ordinal target encoding of F3886 and F3891
        if 'F3886' in df_copy.columns and y is not None:
            temp_df = pd.DataFrame({'F3886': df_copy['F3886'], 'target': y})
            f3886_rates = temp_df.groupby('F3886')['target'].mean().sort_values()
            self.f3886_encoding = {cat: rank for rank, cat in enumerate(f3886_rates.index)}
            df_copy['F3886'] = df_copy['F3886'].map(self.f3886_encoding).fillna(0).astype(int)
        elif 'F3886' in df_copy.columns:
            df_copy['F3886'] = 0
            
        if 'F3891' in df_copy.columns and y is not None:
            temp_df = pd.DataFrame({'F3891': df_copy['F3891'], 'target': y})
            f3891_rates = temp_df.groupby('F3891')['target'].mean().sort_values()
            self.f3891_encoding = {cat: rank for rank, cat in enumerate(f3891_rates.index)}
            df_copy['F3891'] = df_copy['F3891'].map(self.f3891_encoding).fillna(0).astype(int)
        elif 'F3891' in df_copy.columns:
            df_copy['F3891'] = 0
            
        # 6. Compute account tenure in days from F3888
        if 'F3888' in df_copy.columns:
            parsed_dates = pd.to_datetime(df_copy['F3888'], format='%m-%d-%Y', errors='coerce')
            ref_date = pd.to_datetime('2024-01-01')
            median_date = parsed_dates.dropna().median()
            parsed_dates = parsed_dates.fillna(median_date if not pd.isna(median_date) else ref_date)
            df_copy['tenure_days'] = (ref_date - parsed_dates).dt.days
            df_copy = df_copy.drop(columns=['F3888'])
            
        # 7. Compute product complexity
        existing_complexity_cols = [c for c in self.complexity_cols if c in df_copy.columns]
        if existing_complexity_cols:
            df_copy['product_complexity'] = df_copy[existing_complexity_cols].fillna(0).sum(axis=1)
            
        # 8. Compute peer deviation composite
        existing_peer_dev_cols = [c for c in self.peer_dev_cols if c in df_copy.columns]
        if existing_peer_dev_cols:
            df_copy['peer_deviation_composite'] = df_copy[existing_peer_dev_cols].abs().fillna(0).mean(axis=1)
            
        # Convert remaining object columns
        for col in df_copy.columns:
            if df_copy[col].dtype == 'object':
                df_copy[col] = pd.factorize(df_copy[col])[0]
            df_copy[col] = df_copy[col].fillna(0)
            
        self.fitted = True
        
        # If columns_to_keep is specified, ensure we only return those columns in the correct order
        if columns_to_keep is not None:
            self.feature_names_ = list(columns_to_keep)
            # If any are missing, fill with 0
            for col in self.feature_names_:
                if col not in df_copy.columns:
                    df_copy[col] = 0.0
            df_copy = df_copy[self.feature_names_]
        else:
            self.feature_names_ = list(df_copy.columns)
            
        return df_copy, y

    def transform(self, df):
        if not self.fitted:
            raise ValueError("FraudPreprocessor is not fitted yet. Call fit_transform first.")
            
        df_copy = df.copy()
        
        # Drop target if present
        if self.target_col in df_copy.columns:
            df_copy = df_copy.drop(columns=[self.target_col])
            
        # Drop index if present
        index_col = 'Unnamed: 0'
        if index_col in df_copy.columns:
            df_copy = df_copy.drop(columns=[index_col])
            
        # Determine needed raw columns based on self.feature_names_
        needed_raw_cols = set()
        for col in self.feature_names_:
            if col.endswith('_missing'):
                base_col = col[:-8]
                needed_raw_cols.add(base_col)
            elif col == 'product_complexity':
                needed_raw_cols.update(self.complexity_cols)
            elif col == 'peer_deviation_composite':
                needed_raw_cols.update(self.peer_dev_cols)
            elif col == 'tenure_days':
                needed_raw_cols.add('F3888')
            else:
                needed_raw_cols.add(col)
                
        # Only keep columns in df_copy that are in needed_raw_cols
        cols_present = [c for c in df_copy.columns if c in needed_raw_cols]
        df_copy = df_copy[cols_present]
        
        # 3. Velocity ratio features
        existing_velocity_cols = [c for c in self.velocity_cols if c in df_copy.columns]
        for col in existing_velocity_cols:
            df_copy[col] = df_copy[col].fillna(0.5)
            
        # 4. Missingness indicators
        if self.missingness_cols:
            df_dict = {col: df_copy[col].values for col in df_copy.columns}
            for col in self.missingness_cols:
                if col in df.columns:
                    df_dict[f"{col}_missing"] = df[col].isna().astype(np.int8).values
                else:
                    df_dict[f"{col}_missing"] = np.zeros(len(df_copy), dtype=np.int8)
            df_copy = pd.DataFrame(df_dict, index=df_copy.index)
            del df_dict
            import gc; gc.collect()
            
        # 5. Metadata category mapping
        if 'F3886' in df_copy.columns:
            df_copy['F3886'] = df_copy['F3886'].map(self.f3886_encoding).fillna(0).astype(int)
        if 'F3891' in df_copy.columns:
            df_copy['F3891'] = df_copy['F3891'].map(self.f3891_encoding).fillna(0).astype(int)
            
        # 6. Compute account tenure
        if 'F3888' in df_copy.columns:
            parsed_dates = pd.to_datetime(df_copy['F3888'], format='%m-%d-%Y', errors='coerce')
            ref_date = pd.to_datetime('2024-01-01')
            df_copy['tenure_days'] = (ref_date - parsed_dates).dt.days.fillna(0)
            df_copy = df_copy.drop(columns=['F3888'])
            
        # 7. Compute product complexity
        existing_complexity_cols = [c for c in self.complexity_cols if c in df_copy.columns]
        if existing_complexity_cols:
            df_copy['product_complexity'] = df_copy[existing_complexity_cols].fillna(0).sum(axis=1)
            
        # 8. Compute peer deviation composite
        existing_peer_dev_cols = [c for c in self.peer_dev_cols if c in df_copy.columns]
        if existing_peer_dev_cols:
            df_copy['peer_deviation_composite'] = df_copy[existing_peer_dev_cols].abs().fillna(0).mean(axis=1)
            
        # Convert other object columns
        for col in df_copy.columns:
            if df_copy[col].dtype == 'object':
                df_copy[col] = pd.factorize(df_copy[col])[0]
            df_copy[col] = df_copy[col].fillna(0)
            
        # Ensure the feature columns match the fitted columns exactly
        for col in self.feature_names_:
            if col not in df_copy.columns:
                df_copy[col] = 0.0
                
        df_copy = df_copy[self.feature_names_]
        return df_copy

    def save(self, path):
        joblib.dump(self, path)
        print(f"Saved FraudPreprocessor to {path}")

    @staticmethod
    def load(path):
        preprocessor = joblib.load(path)
        print(f"Loaded FraudPreprocessor from {path}")
        return preprocessor
