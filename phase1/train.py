# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
import os
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    confusion_matrix, classification_report, precision_recall_curve
)
# pyrefly: ignore [missing-import]
from imblearn.over_sampling import SMOTE
import lightgbm as lgb
import optuna
# pyrefly: ignore [missing-import]
import shap
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

def main():
    # Settings and Directories
    os.makedirs("plots", exist_ok=True)
    dataset_path = r"d:\down\DataSet.csv"
    
    print("==================================================")
    print("FraudGraph Shield - Phase 1: Model Training & Validation")
    print("==================================================")
    
    # 1. Load raw dataset with memory optimization (pre-detecting dtypes)
    print(f"Loading raw dataset from {dataset_path}...")
    preview = pd.read_csv(dataset_path, nrows=5)
    
    # Check if we can reuse selected features to save memory and time
    selected_features_path = "selected_features.joblib"
    use_cols = None
    if os.path.exists(selected_features_path):
        print(f"Found saved feature list '{selected_features_path}'. Loading only required raw columns to optimize memory.")
        try:
            top_300 = joblib.load(selected_features_path)
            complexity_cols = [f'F{i}' for i in range(3900, 3925)]
            peer_dev_cols = [f'F{i}' for i in range(3880, 3886)]
            needed_raw = {'F3897'}
            for col in top_300:
                if col.endswith('_missing'):
                    needed_raw.add(col[:-8])
                elif col == 'product_complexity':
                    needed_raw.update(complexity_cols)
                elif col == 'peer_deviation_composite':
                    needed_raw.update(peer_dev_cols)
                elif col == 'tenure_days':
                    needed_raw.add('F3888')
                else:
                    needed_raw.add(col)
            use_cols = [c for c in needed_raw if c in preview.columns]
        except Exception as e:
            print(f"Warning: Could not parse saved features, loading full dataset. Error: {e}")
            use_cols = None

    dtypes = {}
    for col in preview.columns:
        if not pd.api.types.is_object_dtype(preview[col]):
            dtypes[col] = np.float32
            
    if use_cols is not None:
        df = pd.read_csv(dataset_path, usecols=use_cols, dtype=dtypes)
    else:
        df = pd.read_csv(dataset_path, dtype=dtypes)
        
    print(f"Dataset shape: {df.shape}")
    
    # 2. Extract features and target, binarize target
    print("Binarizing target column F3897...")
    target_col = 'F3897'
    y = (df[target_col] > 0).astype(int)
    X_raw = df.drop(columns=[target_col])
    
    # Drop leak columns and index column
    leak_cols = ['F3916', 'F3917', 'F3895', 'F3896']
    for col in leak_cols:
        if col in X_raw.columns:
            X_raw = X_raw.drop(columns=[col])
            
    # Drop index column if present
    if 'Unnamed: 0' in X_raw.columns:
        X_raw = X_raw.drop(columns=['Unnamed: 0'])
        
    print(f"Target distribution after binarizing: {np.bincount(y)}")
    
    # 3. Train/Test Stratified Split (80% Train+Val, 20% Holdout Test)
    print("Performing stratified split: 80% train+validation, 20% holdout test...")
    X_train_val_raw, X_test_raw, y_train_val, y_test = train_test_split(
        X_raw, y, test_size=0.20, stratify=y, random_state=42
    )
    print(f"Train+Val set shape: {X_train_val_raw.shape}, Test set shape: {X_test_raw.shape}")
    
    # 4. Feature Selection Round 1: Filter columns with >95% NA or zero variance
    from feature_selection import run_round_1_filter
    
    # Combine train_val raw with target for filter calculation
    train_val_raw_df = X_train_val_raw.copy()
    train_val_raw_df[target_col] = y_train_val
    
    selected_cols_r1, cols_dropped_r1 = run_round_1_filter(train_val_raw_df, target_col)
    
    # Drop from training and test sets
    X_train_val_r1 = X_train_val_raw[[c for c in selected_cols_r1 if c != target_col]]
    X_test_r1 = X_test_raw[[c for c in selected_cols_r1 if c != target_col]]
    
    # Add target back for the preprocessor fitting
    train_val_df_r1 = X_train_val_r1.copy()
    train_val_df_r1[target_col] = y_train_val
    
    # 5. Preprocess (Fit on 80% training data)
    from preprocessor import FraudPreprocessor
    print("Fitting FraudPreprocessor on 80% train+validation set...")
    preprocessor = FraudPreprocessor()
    X_train_val_prep, _ = preprocessor.fit_transform(train_val_df_r1)
    
    # 6. Feature Selection Round 2: LightGBM feature importance to keep top 300
    from feature_selection import run_round_2_lgb_importance
    top_300_cols, importance_df = run_round_2_lgb_importance(X_train_val_prep, y_train_val, top_n=300)
    
    # Save the selected feature names
    joblib.dump(top_300_cols, "selected_features.joblib")
    print("Saved selected top 300 features list to 'selected_features.joblib'")
    
    # Save Feature Importance Plot
    plt.figure(figsize=(12, 8))
    sns.barplot(
        x='importance', y='feature', 
        data=importance_df.head(30), 
        palette='viridis'
    )
    plt.title('Top 30 Feature Importances (Round 2 selection)')
    plt.tight_layout()
    plt.savefig("plots/feature_importances_top30.png")
    plt.close()
    
    # Restrict preprocessed features to top 300
    X_train_val_top = X_train_val_prep[top_300_cols]
    
    # Free up memory
    del X_train_val_raw, X_test_raw, df, X_raw, train_val_raw_df
    import gc
    gc.collect()
    
    # 7. Model Training and Cross-Validation (Days 7–9)
    # Perform 5-fold Stratified CV on the 80% portion using initial parameters
    print("\n--------------------------------------------------")
    print("Running 5-fold Stratified Cross-Validation on Initial Hyperparameters...")
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_auc_scores = []
    
    initial_params = {
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
    
    for fold, (train_idx, val_idx) in enumerate(cv.split(X_train_val_r1, y_train_val)):
        # Split raw folds (so preprocessor is fitted only on the training fold)
        X_tr_raw = X_train_val_r1.iloc[train_idx].copy()
        y_tr = y_train_val.iloc[train_idx]
        X_tr_raw[target_col] = y_tr
        
        X_va_raw = X_train_val_r1.iloc[val_idx]
        y_va = y_train_val.iloc[val_idx]
        
        # Fit preprocessor on training fold
        fold_preprocessor = FraudPreprocessor()
        X_tr_prep, _ = fold_preprocessor.fit_transform(X_tr_raw, columns_to_keep=top_300_cols)
        X_va_prep = fold_preprocessor.transform(X_va_raw)
        
        # Keep only the top 300 features
        X_tr_prep = X_tr_prep[top_300_cols]
        X_va_prep = X_va_prep[top_300_cols]
        
        # Apply SMOTE to training fold only
        smote = SMOTE(random_state=42)
        X_tr_smote, y_tr_smote = smote.fit_resample(X_tr_prep, y_tr)
        
        # Train model
        model = lgb.LGBMClassifier(**initial_params)
        model.fit(
            X_tr_smote, y_tr_smote,
            eval_set=[(X_va_prep, y_va)],
            callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
        )
        
        # Predict on validation fold
        preds_val = model.predict_proba(X_va_prep)[:, 1]
        auc = roc_auc_score(y_va, preds_val)
        cv_auc_scores.append(auc)
        print(f"  Fold {fold+1} Validation AUC-ROC: {auc:.4f}")
        
        # Memory cleanup inside fold
        del fold_preprocessor, X_tr_prep, X_va_prep, X_tr_smote, model, X_tr_raw, X_va_raw
        import gc; gc.collect()
        
    mean_cv_auc = np.mean(cv_auc_scores)
    std_cv_auc = np.std(cv_auc_scores)
    print(f"Mean CV AUC-ROC: {mean_cv_auc:.4f} ± {std_cv_auc:.4f}")
    
    if mean_cv_auc < 0.85:
        print("WARNING: Mean CV AUC is below 0.85! Checking preprocessing recommended.")
    else:
        print("Mean CV AUC is above 0.85. Proceeding to hyperparameter tuning...")
        
    # 8. Hyperparameter Tuning (Days 10–11)
    print("\n--------------------------------------------------")
    print("Running Bayesian Hyperparameter Optimization with Optuna (max 20 trials)...")
    
    # 3-Fold Stratified CV pre-split and preprocessed for speed
    print("Pre-preprocessing Optuna CV folds...")
    optuna_cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    optuna_folds = []
    for tr_idx, va_idx in optuna_cv.split(X_train_val_r1, y_train_val):
        X_tr_raw = X_train_val_r1.iloc[tr_idx].copy()
        y_tr = y_train_val.iloc[tr_idx]
        X_tr_raw[target_col] = y_tr
        
        X_va_raw = X_train_val_r1.iloc[va_idx]
        y_va = y_train_val.iloc[va_idx]
        
        fold_prep = FraudPreprocessor()
        X_tr_prep, _ = fold_prep.fit_transform(X_tr_raw, columns_to_keep=top_300_cols)
        X_va_prep = fold_prep.transform(X_va_raw)
        
        # Keep only the top 300 features
        X_tr_prep = X_tr_prep[top_300_cols]
        X_va_prep = X_va_prep[top_300_cols]
        
        # Apply SMOTE once
        smote = SMOTE(random_state=42)
        X_tr_smote, y_tr_smote = smote.fit_resample(X_tr_prep, y_tr)
        
        optuna_folds.append((X_tr_smote, y_tr_smote, X_va_prep, y_va))
        
    def objective(trial):
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'num_leaves': trial.suggest_int('num_leaves', 31, 127),
            'max_depth': trial.suggest_int('max_depth', 4, 8),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
            'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 0.95),
            'min_child_samples': trial.suggest_int('min_child_samples', 20, 100),
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'class_weight': 'balanced',
            'n_estimators': 500,
            'verbose': -1,
            'random_state': 42
        }
        
        trial_aucs = []
        best_iterations = []
        
        for X_tr_smote, y_tr_smote, X_va_prep, y_va in optuna_folds:
            model = lgb.LGBMClassifier(**params)
            model.fit(
                X_tr_smote, y_tr_smote,
                eval_set=[(X_va_prep, y_va)],
                callbacks=[lgb.early_stopping(50, verbose=False)]
            )
            
            preds_va = model.predict_proba(X_va_prep)[:, 1]
            trial_aucs.append(roc_auc_score(y_va, preds_va))
            best_iterations.append(model.best_iteration_)
            
            del model
            import gc
            gc.collect()
            
        trial.set_user_attr('best_iteration', int(np.mean(best_iterations)))
        mean_auc = np.mean(trial_aucs)
        print(f"  Trial {trial.number+1}/20: Mean AUC-ROC = {mean_auc:.4f} (avg trees: {trial.user_attrs['best_iteration']})")
        import gc
        gc.collect()
        return mean_auc

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=20)
    
    print("\nOptuna Hyperparameter Tuning Complete!")
    print(f"Best Trial AUC-ROC: {study.best_value:.4f}")
    best_params = study.best_params
    best_n_estimators = study.best_trial.user_attrs.get('best_iteration', 200)
    print("Best Hyperparameters:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"Optimal n_estimators (early stopping average): {best_n_estimators}")
    
    # 9. Train Final Model on the entire 80% Train+Val Set
    print("\n--------------------------------------------------")
    print("Training final model on full 80% train+validation set with optimal hyperparameters...")
    
    # Re-fit preprocessor on the full 80% training set
    final_preprocessor = FraudPreprocessor()
    X_train_val_prep, _ = final_preprocessor.fit_transform(train_val_df_r1, columns_to_keep=top_300_cols)
    X_train_val_top = X_train_val_prep[top_300_cols]
    
    # Apply SMOTE to the entire 80% training set
    smote = SMOTE(random_state=42)
    X_final_smote, y_final_smote = smote.fit_resample(X_train_val_top, y_train_val)
    
    # Assemble final parameters
    final_model_params = {
        'objective': 'binary',
        'metric': 'auc',
        'n_estimators': best_n_estimators,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'class_weight': 'balanced',
        'verbose': -1,
        'random_state': 42,
        **best_params
    }
    
    final_model = lgb.LGBMClassifier(**final_model_params)
    final_model.fit(X_final_smote, y_final_smote)
    
    # Save the final preprocessor and model production artifacts
    final_preprocessor.save("preprocessor.joblib")
    joblib.dump(final_model, "model.joblib")
    print("Production artifacts saved successfully ('preprocessor.joblib', 'model.joblib').")
    
    # 10. Evaluate on the 20% Holdout Test Set
    print("\nEvaluating model performance on the 20% holdout test set...")
    X_test_prep = final_preprocessor.transform(X_test_r1)
    X_test_top = X_test_prep[top_300_cols]
    
    test_probs = final_model.predict_proba(X_test_top)[:, 1]
    test_preds = (test_probs >= 0.5).astype(int)
    
    test_auc = roc_auc_score(y_test, test_probs)
    test_f1 = f1_score(y_test, test_preds)
    test_prec = precision_score(y_test, test_preds)
    test_rec = recall_score(y_test, test_preds)
    
    print("\n================ TEST SET METRICS ================")
    print(f"Test AUC-ROC: {test_auc:.4f}")
    print(f"Test F1-score: {test_f1:.4f}")
    print(f"Test Precision: {test_prec:.4f}")
    print(f"Test Recall: {test_rec:.4f}")
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, test_preds)
    print(cm)
    print("\nClassification Report:")
    print(classification_report(y_test, test_preds))
    print("==================================================")
    
    # Threshold Analysis
    print("\nPerforming threshold analysis (0.3, 0.4, 0.5, 0.6)...")
    thresholds = [0.3, 0.4, 0.5, 0.6]
    threshold_results = []
    for t in thresholds:
        t_preds = (test_probs >= t).astype(int)
        t_prec = precision_score(y_test, t_preds)
        t_rec = recall_score(y_test, t_preds)
        t_f1 = f1_score(y_test, t_preds)
        t_cm = confusion_matrix(y_test, t_preds)
        print(f"Threshold {t:.1f} -> Precision: {t_prec:.4f}, Recall: {t_rec:.4f}, F1: {t_f1:.4f}, Flagged: {t_preds.sum()}")
        threshold_results.append({
            'threshold': t,
            'precision': t_prec,
            'recall': t_rec,
            'f1': t_f1,
            'confusion_matrix': t_cm.tolist()
        })
        
    # Generate and save diagnostic curves
    # ROC Curve & Precision-Recall Curve
    precision, recall, _ = precision_recall_curve(y_test, test_probs)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # ROC
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(y_test, test_probs)
    axes[0].plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {test_auc:.4f})')
    axes[0].plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    axes[0].set_xlim([0.0, 1.0])
    axes[0].set_ylim([0.0, 1.05])
    axes[0].set_xlabel('False Positive Rate')
    axes[0].set_ylabel('True Positive Rate')
    axes[0].set_title('Receiver Operating Characteristic (ROC) Curve')
    axes[0].legend(loc="lower right")
    
    # PR
    axes[1].plot(recall, precision, color='blue', lw=2, label='PR curve')
    axes[1].set_xlabel('Recall')
    axes[1].set_ylabel('Precision')
    axes[1].set_title('Precision-Recall Curve')
    axes[1].set_xlim([0.0, 1.0])
    axes[1].set_ylim([0.0, 1.05])
    axes[1].legend(loc="lower left")
    
    plt.tight_layout()
    plt.savefig("plots/model_curves.png")
    plt.close()
    
    # 11. SHAP Analysis (Day 12)
    print("\nRunning SHAP explainability analysis on test set...")
    try:
        explainer = shap.TreeExplainer(final_model)
        shap_values = explainer(X_test_top)
        
        # Save explainer
        joblib.dump(explainer, "explainer.joblib")
        print("Saved SHAP explainer production artifact to 'explainer.joblib'")
        
        # Save Beeswarm plot
        plt.figure(figsize=(10, 6))
        shap.plots.beeswarm(shap_values, max_display=20, show=False)
        plt.title("Global SHAP Summary Plot (Top 20 Features)")
        plt.tight_layout()
        plt.savefig("plots/shap_summary_beeswarm.png", bbox_inches='tight')
        plt.close()
        
        # Save Bar plot
        plt.figure(figsize=(10, 6))
        shap.plots.bar(shap_values, max_display=20, show=False)
        plt.title("SHAP Feature Importance (Top 20)")
        plt.tight_layout()
        plt.savefig("plots/shap_bar_plot.png", bbox_inches='tight')
        plt.close()
        
        # Save Waterfall plot for a True Positive
        # Locate true positive indices
        tp_indices = np.where((y_test == 1) & (test_preds == 1))[0]
        if len(tp_indices) > 0:
            tp_idx = tp_indices[0]
            plt.figure(figsize=(10, 6))
            shap.plots.waterfall(shap_values[tp_idx], max_display=10, show=False)
            plt.title(f"SHAP Waterfall Plot for True Positive Account (Index {tp_idx})")
            plt.tight_layout()
            plt.savefig("plots/shap_waterfall_tp.png", bbox_inches='tight')
            plt.close()
            print(f"SHAP plots generated successfully and saved to 'plots/' directory. TP index used: {tp_idx}")
        else:
            print("No True Positive predictions found in the test set to plot waterfall chart.")
            
    except Exception as e:
        print(f"Error during SHAP plotting: {str(e)}")
        import traceback
        traceback.print_exc()
        
    # 12. Write model_card.md
    generate_model_card(
        initial_params=initial_params,
        best_params=best_params,
        mean_cv_auc=mean_cv_auc,
        std_cv_auc=std_cv_auc,
        test_auc=test_auc,
        test_f1=test_f1,
        test_prec=test_prec,
        test_rec=test_rec,
        cm=cm,
        threshold_results=threshold_results,
        dropped_cols=cols_dropped_r1
    )
    
    print("\nPhase 1 execution complete! Check model_card.md for performance report.")

def generate_model_card(initial_params, best_params, mean_cv_auc, std_cv_auc, 
                        test_auc, test_f1, test_prec, test_rec, cm, threshold_results, dropped_cols):
    model_card_content = f"""# Model Card: FraudGraph Shield Transaction Scorer (Phase 1)

This model card documents the training process, validation results, and explainability assets for the LightGBM transaction risk scoring model.

## Model Details
- **Architecture**: Gradient Boosted Decision Trees (GBDT) using LightGBM.
- **Objective**: Binary classification (0 = Clean, 1 = Suspicious / Fraud).
- **Date Generated**: June 2026
- **Data Source**: [DataSet.csv](file:///d:/down/DataSet.csv) (9,082 records, 3,924 raw features).
- **Target Variable**: Binarized version of `F3897` (value 0 stays 0, values >= 1 binarized to 1).

## Preprocessing Decisions & Rationale
- **Feature Separation**: separated target variable `F3897` from training features.
- **Velocity Ratio Features (`F1-F3885`)**: imputed missing values with `0.5` (neutral value representing no deviation from baseline on a 0–1 velocity scale).
- **Missingness Indicators**: created binary indicators `{{col}}_missing` for any column with >5% missingness.
- **Metadata Encoding**: ordinal target encoding applied to `F3886` (account type) and `F3891` (occupation) based on training fold target rates.
- **Account Tenure**: computed as number of days between account opening date `F3888` and reference date `2024-01-01`.
- **Product Complexity**: count of active product flags across columns `F3900-F3924`.
- **Peer Deviation**: average absolute value of deviation features `F3880-F3885`.

## Feature Selection Summary
- **Round 1 (Filter)**: removed {len(dropped_cols)} features that had >95% NA values or zero variance.
- **Round 2 (LightGBM Importance)**: trained an initial LightGBM on the remaining features and selected the top 300 features by built-in feature importance score.

## Hyperparameters

### Initial Configuration
```python
{initial_params}
```

### Tuned Configuration (via Optuna Bayesian Optimization)
```python
{best_params}
```

## Validation Performance
- **Cross-Validation Scheme**: 5-Fold Stratified Cross-Validation (SMOTE applied strictly inside each training fold).
- **Validation AUC-ROC (Mean ± Std)**: {mean_cv_auc:.5f} ± {std_cv_auc:.5f}

## Holdout Test Set Performance (20% Split)
The model was evaluated on the 20% holdout test set only after hyperparameter tuning completed.

- **Holdout AUC-ROC**: **{test_auc:.5f}** (Target: >0.90, Achieved: {test_auc:.5f})
- **Holdout F1-score**: {test_f1:.5f}
- **Holdout Precision**: {test_prec:.5f}
- **Holdout Recall**: {test_rec:.5f}

### Confusion Matrix
```
[[{cm[0, 0]} {cm[0, 1]}]  (Clean)
 [{cm[1, 0]} {cm[1, 1]}]] (Suspicious/Fraud)
```

### Threshold Analysis
The default classification threshold is 0.5. Depending on the bank's operational capacity and cost of false negatives (missed fraud) vs false positives (incorrectly blocked transactions), a different threshold may be configured:

| Threshold | Precision | Recall | F1-Score | Number Flagged |
|---|---|---|---|---|
"""
    for res in threshold_results:
        model_card_content += f"| {res['threshold']:.1f} | {res['precision']:.4f} | {res['recall']:.4f} | {res['f1']:.4f} | {res['confusion_matrix'][1][1]} (TP) / {res['confusion_matrix'][0][1]+res['confusion_matrix'][1][1]} (total) |\n"
        
    model_card_content += """
## Explainability & Model Interpretability
SHAP analysis was performed on the test set predictions:
1. **Global SHAP Summary Plot (Beeswarm)**: Located at [shap_summary_beeswarm.png](file:///d:/FraudGraphShield/plots/shap_summary_beeswarm.png). Shows overall feature contributions and directional impacts.
2. **Mean Absolute SHAP Bar Plot**: Located at [shap_bar_plot.png](file:///d:/FraudGraphShield/plots/shap_bar_plot.png). Shows the average contribution strength of the top 20 features.
3. **Individual Waterfall Plot**: Located at [shap_waterfall_tp.png](file:///d:/FraudGraphShield/plots/shap_waterfall_tp.png). Shows feature-level risk drivers for a correctly identified suspicious account in the test set.

*All plots, including diagnostic ROC and Precision-Recall curves, are saved in the `plots/` directory.*
"""
    
    card_path = "model_card.md"
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(model_card_content)
    print(f"Model card written successfully to {card_path}")

if __name__ == '__main__':
    main()
