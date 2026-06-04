import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import joblib
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="Predict fraud probabilities using FraudGraph Shield Phase 1 model")
    parser.add_argument("--input", required=True, help="Path to input CSV dataset")
    parser.add_argument("--output", default="predictions.csv", help="Path to save predictions output CSV")
    parser.add_argument("--threshold", type=float, default=0.5, help="Classification threshold (default: 0.5)")
    args = parser.parse_args()
    
    # Load production artifacts
    model_path = "model.joblib"
    prep_path = "preprocessor.joblib"
    
    if not os.path.exists(model_path) or not os.path.exists(prep_path):
        print(f"Error: Model artifacts not found. Please ensure '{model_path}' and '{prep_path}' are in the directory.")
        return
        
    print(f"Loading model from {model_path}...")
    model = joblib.load(model_path)
    print(f"Loading preprocessor from {prep_path}...")
    preprocessor = joblib.load(prep_path)
    
    # Load input dataset
    print(f"Reading input dataset from {args.input}...")
    # Preview to check columns
    preview = pd.read_csv(args.input, nrows=5)
    
    # Determine columns to load to save memory
    needed_raw = set()
    for col in preprocessor.feature_names_:
        if col.endswith('_missing'):
            needed_raw.add(col[:-8])
        elif col == 'product_complexity':
            needed_raw.update(preprocessor.complexity_cols)
        elif col == 'peer_deviation_composite':
            needed_raw.update(preprocessor.peer_dev_cols)
        elif col == 'tenure_days':
            needed_raw.add('F3888')
        else:
            needed_raw.add(col)
            
    # Keep only columns that exist in the preview
    use_cols = [c for c in needed_raw if c in preview.columns]
    missing_cols = [c for c in needed_raw if c not in preview.columns]
    
    if missing_cols:
        print(f"Warning: {len(missing_cols)} expected base features are missing from input dataset. They will be filled with neutral/zero values.")
        
    # Read the file
    dtypes = {}
    for col in preview.columns:
        if col in use_cols and not pd.api.types.is_object_dtype(preview[col]):
            dtypes[col] = np.float32
            
    df_raw = pd.read_csv(args.input, usecols=use_cols, dtype=dtypes)
    print(f"Loaded dataset shape: {df_raw.shape}")
    
    # Preprocess
    print("Preprocessing data...")
    X_prep = preprocessor.transform(df_raw)
    
    # Predict
    print("Generating predictions...")
    probs = model.predict_proba(X_prep)[:, 1]
    preds = (probs >= args.threshold).astype(int)
    
    # Save output
    output_df = pd.DataFrame({
        'Index': df_raw.index if 'Unnamed: 0' not in df_raw.columns else df_raw.get('Unnamed: 0', df_raw.index),
        'Fraud_Probability': probs,
        'Prediction': preds
    })
    
    # If target exists, show evaluation
    target_col = 'F3897'
    if target_col in preview.columns:
        print("Target column F3897 found. Calculating performance metrics...")
        # Read target column
        df_target = pd.read_csv(args.input, usecols=[target_col])
        y_true = (df_target[target_col] > 0).astype(int)
        
        # Defer import to prevent memory consumption on startup
        from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
        auc = roc_auc_score(y_true, probs)
        prec = precision_score(y_true, preds)
        rec = recall_score(y_true, preds)
        f1 = f1_score(y_true, preds)
        
        print(f"\n================ EVALUATION ================")
        print(f"AUC-ROC: {auc:.4f}")
        print(f"Precision: {prec:.4f}")
        print(f"Recall: {rec:.4f}")
        print(f"F1-score: {f1:.4f}")
        print(f"============================================\n")
        
        output_df['True_Label'] = y_true
        
    output_df.to_csv(args.output, index=False)
    print(f"Predictions saved successfully to '{args.output}'!")

if __name__ == '__main__':
    main()
