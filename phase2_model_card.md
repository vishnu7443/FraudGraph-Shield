# Model Card: FraudGraph Shield GNN Graph Engine (Phase 2)

This model card documents the Graph Neural Network (GNN) model architecture, graph topology statistics, holdout test performance, and pipeline latency metrics for Phase 2 of the FraudGraph Shield platform.

## Model Details
- **Architecture**: GraphSAGE (Graph Sample and Aggregate) with 3 message-passing layers.
  - Layer 1: SAGEConv (74 in_channels -> 128 hidden_channels) + ReLU + Dropout (0.3)
  - Layer 2: SAGEConv (128 hidden_channels -> 128 hidden_channels) + ReLU + Dropout (0.3)
  - Layer 3: SAGEConv (128 hidden_channels -> 64 hidden_channels) + ReLU
  - Output Layer: Linear classifier (64 -> 1 out_channels) + Sigmoid activation.
- **Objective**: Semi-supervised node classification (0 = Clean, 1 = Mule Account).
- **Date Generated**: June 2026
- **Data Source**: [DataSet.csv](file:///d:/down/DataSet.csv) (9,082 records, 3,924 raw features).
- **Target Variable**: Binarized version of `F3897` (value 0 represents clean, >= 1 represents suspicious/mule activity).

## Node Feature Assembly
Each account node is represented by a 74-dimensional normalized feature vector:
1. **Top 64 SHAP Tabular Features**: Extracted from the preprocessed Phase 1 LightGBM dataset.
2. **6 Engineered Structural Features**:
   - Tenure in days (relative to `2024-01-01`).
   - Active product ownership complexity score.
   - Peer deviation composite score.
   - Target-encoded occupation class probability.
   - Target-encoded account type class probability.
   - Credit score bucket.
3. **2 Temporal Hop Velocity Signature (THVS) Features**:
   - Hop speed ratio (relative short-window velocity / long-window velocity).
   - Amount retention ratio (net debits / cumulative credits).
4. **LightGBM Scorer Output**: Continuous risk probability from the Phase 1 model.
5. **High Velocity Flag**: Binary indicator for high-velocity outlier activity.

---

## Graph Topology & Statistics
The transaction network is built dynamically utilizing proximity and co-occurrence rules:
- **Nodes (Accounts)**: 9,082
- **Edges (Proximity Links)**: 68,721
- **Average Total Degree**: **`15.1335`** (Target: `[8, 25]` — **PASSED**)
- **Average Clustering Coefficient**: **`0.4125`**
- **Edge Composition**:
  - *Layer 1*: Proximity similarity (cosine distance threshold >= 0.85 on top 50 SHAP features).
  - *Layer 2*: Risk and tenure proximity (same risk label, same account type, tenure opened within 90 days, capped to at most 3 neighbors).
  - *Layer 3*: Demographic co-occurrence (same occupation, same credit score bucket, flagged risk class, capped to at most 3 neighbors).

---

## Model Performance

### Holdout Test Split Metrics (20% Stratified Holdout)
Evaluated on the test node mask representing unseen accounts during GNN training:

- **Test AUC-ROC**: **`0.9999`**
- **Test Average Precision (AP)**: **`0.9998`**

### Threshold Analysis
Depending on operational risk tolerance, the classification threshold can be adjusted:

| Threshold | Precision | Recall | F1-Score | Status / Operational Decision |
|---|---|---|---|---|
| **0.3** | 99.05% | 99.05% | 99.05% | High recall, captures almost all mules |
| **0.4** | 99.04% | 98.57% | 98.81% | Balanced trade-off |
| **0.5** (Default) | 99.28% | 98.33% | 98.80% | Standard configuration |
| **0.6** | 99.28% | 98.33% | 98.80% | High precision watch-list |
| **0.7** | 99.28% | 98.33% | 98.80% | Extremely high confidence freeze |

---

## Inference Pipeline Latency
The complete real-time scoring latency has been optimized for sub-150ms constraints:

- **Preprocessor Transform**: **`40.04 ms`** (vectorized fillna, target-level missingness, fast datetime split parser).
- **LightGBM Scorer**: **`3.81 ms`**
- **GNN Node Inference**: **`45.17 ms`** (single-node GraphSAGE forward pass).
- **Total Combined Latency**: **`89.02 ms`** (Target: `<150ms` — **PASSED**)

---

## Explainability and Diagnostics
- **Mule Clusters Plots**: Saved in `plots/cluster_1.png` to `plots/cluster_5.png`. Visualizes 2-hop neighborhoods colored by GNN mule probabilities.
- **Fail-safe Logic**: Complemented by a parallel scikit-learn Isolation Forest anomaly scorer. Node scores and predictions are fed into the downstream Risk Fusion engine for Phase 3.
