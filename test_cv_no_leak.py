# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
from sklearn.model_selection import StratifiedKFold
# pyrefly: ignore [missing-import]
from sklearn.metrics import roc_auc_score
# pyrefly: ignore [missing-import]
from imblearn.over_sampling import SMOTE
# pyrefly: ignore [missing-import]
import lightgbm as lgb
from preprocessor import FraudPreprocessor
from feature_selection import run_round_1_filter, run_round_2_lgb_importance
import gc

path = r"d:\down\DataSet.csv"
print("Loading dataset...")
df = pd.read_csv(path)
y = (df['F3897'] > 0).astype(int)

# Convert all float64 columns to float32 to reduce memory footprint by 50%
float_cols = df.select_dtypes(include=['float64']).columns
df[float_cols] = df[float_cols].astype(np.float32)
print("Converted float64 columns to float32 to save memory.")

# Drop index, F3916, F3917, and F3895, F3896
df_clean = df.drop(columns=['F3897', 'Unnamed: 0'])
leak_cols = ['F3916', 'F3917', 'F3895', 'F3896']
for col in leak_cols:
    if col in df_clean.columns:
        df_clean = df_clean.drop(columns=[col])

print("Running Round 1 Filter...")
df_clean['F3897'] = y  # Add target back for filter
selected_cols, _ = run_round_1_filter(df_clean, 'F3897')

# Drop from df_clean before preprocessing to save memory
X_r1 = df_clean[[c for c in selected_cols if c != 'F3897']]

# Free raw df memory
del df
gc.collect()

print("Preprocessing...")
prep = FraudPreprocessor()
X_prep, _ = prep.fit_transform(df_clean)  # fit on clean

# Free df_clean memory
del df_clean
gc.collect()

print("Running Round 2 Selection...")
top_300, _ = run_round_2_lgb_importance(X_prep, y, top_n=300)

# Free X_prep memory
del X_prep
gc.collect()

print("\nRunning 5-fold CV without leaky columns...")
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
aucs = []

params = {
    'objective': 'binary',
    'metric': 'auc',
    'num_leaves': 63,
    'max_depth': 6,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'class_weight': 'balanced',
    'n_estimators': 500,
    'early_stopping_rounds': 50,
    'verbose': -1,
    'random_state': 42
}

for fold, (train_idx, val_idx) in enumerate(cv.split(X_r1, y)):
    # Slice train/val
    X_tr, y_tr = X_r1.iloc[train_idx].copy(), y.iloc[train_idx]
    X_tr['F3897'] = y_tr
    X_va, y_va = X_r1.iloc[val_idx], y.iloc[val_idx]
    
    fold_prep = FraudPreprocessor()
    X_tr_prep, _ = fold_prep.fit_transform(X_tr)
    X_va_prep = fold_prep.transform(X_va)
    
    # Restrict to top 300
    cols_to_use = [c for c in top_300 if c in X_tr_prep.columns]
    X_tr_prep = X_tr_prep[cols_to_use]
    X_va_prep = X_va_prep[cols_to_use]
    
    smote = SMOTE(random_state=42)
    X_tr_smote, y_tr_smote = smote.fit_resample(X_tr_prep, y_tr)
    
    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_tr_smote, y_tr_smote,
        eval_set=[(X_va_prep, y_va)],
        callbacks=[lgb.early_stopping(50, verbose=False)]
    )
    
    preds = model.predict_proba(X_va_prep)[:, 1]
    auc = roc_auc_score(y_va, preds)
    aucs.append(auc)
    print(f"Fold {fold+1} AUC-ROC: {auc:.4f}")
    
    del fold_prep, X_tr_prep, X_va_prep, X_tr_smote, model, X_tr, X_va
    gc.collect()
    
print(f"Mean AUC-ROC: {np.mean(aucs):.4f} ± {np.std(aucs):.4f}")
