# Model Card: FraudGraph Shield Transaction Scorer (Phase 1)

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
- **Missingness Indicators**: created binary indicators `{col}_missing` for any column with >5% missingness.
- **Metadata Encoding**: ordinal target encoding applied to `F3886` (account type) and `F3891` (occupation) based on training fold target rates.
- **Account Tenure**: computed as number of days between account opening date `F3888` and reference date `2024-01-01`.
- **Product Complexity**: count of active product flags across columns `F3900-F3924`.
- **Peer Deviation**: average absolute value of deviation features `F3880-F3885`.

## Feature Selection Summary
- **Round 1 (Filter)**: removed 1 features that had >95% NA values or zero variance.
- **Round 2 (LightGBM Importance)**: trained an initial LightGBM on the remaining features and selected the top 300 features by built-in feature importance score.

## Hyperparameters

### Initial Configuration
```python
{'objective': 'binary', 'metric': 'auc', 'num_leaves': 63, 'max_depth': 6, 'learning_rate': 0.05, 'feature_fraction': 0.8, 'bagging_fraction': 0.8, 'bagging_freq': 5, 'class_weight': 'balanced', 'n_estimators': 500, 'early_stopping_rounds': 50, 'verbose': -1, 'random_state': 42}
```

### Tuned Configuration (via Optuna Bayesian Optimization)
```python
{'num_leaves': 97, 'max_depth': 7, 'learning_rate': 0.030205901340622576, 'feature_fraction': 0.7878793004212264, 'min_child_samples': 71}
```

## Validation Performance
- **Cross-Validation Scheme**: 5-Fold Stratified Cross-Validation (SMOTE applied strictly inside each training fold).
- **Validation AUC-ROC (Mean ± Std)**: 0.83620 ± 0.02293

## Holdout Test Set Performance (20% Split)
The model was evaluated on the 20% holdout test set only after hyperparameter tuning completed.

- **Holdout AUC-ROC**: **0.82649** (Target: >0.90, Achieved: 0.82649)
- **Holdout F1-score**: 0.51448
- **Holdout Precision**: 0.90419
- **Holdout Recall**: 0.35952

### Confusion Matrix
```
[[1381 16]  (Clean)
 [269 151]] (Suspicious/Fraud)
```

### Threshold Analysis
The default classification threshold is 0.5. Depending on the bank's operational capacity and cost of false negatives (missed fraud) vs false positives (incorrectly blocked transactions), a different threshold may be configured:

| Threshold | Precision | Recall | F1-Score | Number Flagged |
|---|---|---|---|---|
| 0.3 | 0.6063 | 0.5500 | 0.5768 | 231 (TP) / 381 (total) |
| 0.4 | 0.7768 | 0.4143 | 0.5404 | 174 (TP) / 224 (total) |
| 0.5 | 0.9042 | 0.3595 | 0.5145 | 151 (TP) / 167 (total) |
| 0.6 | 0.9720 | 0.3310 | 0.4938 | 139 (TP) / 143 (total) |

## Explainability & Model Interpretability
SHAP analysis was performed on the test set predictions:
1. **Global SHAP Summary Plot (Beeswarm)**: Located at [shap_summary_beeswarm.png](file:///d:/FraudGraphShield/plots/shap_summary_beeswarm.png). Shows overall feature contributions and directional impacts.
2. **Mean Absolute SHAP Bar Plot**: Located at [shap_bar_plot.png](file:///d:/FraudGraphShield/plots/shap_bar_plot.png). Shows the average contribution strength of the top 20 features.
3. **Individual Waterfall Plot**: Located at [shap_waterfall_tp.png](file:///d:/FraudGraphShield/plots/shap_waterfall_tp.png). Shows feature-level risk drivers for a correctly identified suspicious account in the test set.

*All plots, including diagnostic ROC and Precision-Recall curves, are saved in the `plots/` directory.*
