# 🛡️ FraudGraph Shield: End-to-End Transaction Scorer & Mule Detector

FraudGraph Shield is a production-grade, multi-stage machine learning system designed to detect fraudulent transactions and money mule accounts for banking institutions and small businesses. The system integrates high-dimensional tabular classification, deep graph learning (GNN), real-time API services, and interactive analyst dashboards following a strict agentic workflow: **Think → Decide → Act → Observe**.

---

## 📊 Project Architecture Overview

The platform is divided into 4 sequential developmental phases:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                PHASE 1: DATA & TABULAR MODEL                    │
│ [Raw CSV Data] ──> [Preprocessor] ──> [Feature Selection] ──> [LightGBM Model]   │
└────────────────────────┬───────────────────────────────────┬────────────────────┘
                         │                                   │
                         ▼ (Top SHAP features & scores)       ▼ (LGBM Scores)
┌────────────────────────────────────────────────────────────┴────────────────────┐
│                                PHASE 2: GRAPH NEURAL NETWORK                    │
│ [Account Graph Construction] ──> [Node Feature Assembly] ──> [GraphSAGE Model]  │
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼ (GNN Mule Scores)
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                PHASE 3: RISK FUSION API ENGINE                  │
│ [FastAPI Backend] <── [Risk Fusion Engine (LGBM + GNN + CFMS)] <── [Redis Cache] │
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼ (Scores & Explanations)
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                PHASE 4: ANALYST STREAMLIT UI                    │
│ [Risk Queue] ──> [Account Deep-Dive & SHAP] ──> [Network Graph] ──> [Telemetry] │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Phase 1: Tabular Machine Learning (LightGBM)

Phase 1 establishes the baseline transaction scorer using a state-preserving LightGBM classifier.

* **State-Preserving Transformer (`preprocessor.py`)**: Handles extreme missingness (neutral imputation, e.g., filling velocity features `F1-F3885` with a neutral `0.5`) and maps categories (`Account Type` `F3886`, `Occupation` `F3891`) using target ordinal probability encoding inside cross-validation folds to prevent data leakage.
* **Two-Stage Feature Selection**:
  * **Round 1 (Filter)**: Eliminates features with `>95% missingness` or constant variance.
  * **Round 2 (LightGBM Gain/Split Importance)**: Fits a baseline tree model and extracts the **top 300** predictive features from 3,924 raw columns.
* **SMOTE + Stratified 5-Fold Cross-Validation**: Addresses severe class imbalance (under 3% fraud rate) and prevents target leakage.
* **Hyperparameter Tuning**: Run via **Optuna** Bayesian optimization.
* **Performance on Holdout Test Set**:
  * **AUC-ROC**: `0.8113`
  * **Precision**: `75.68%`
  * **Recall**: `40.00%` (Default `0.5` threshold)
* **Interpretability**: Leverages global and local **SHAP** values to extract top feature contributions.

---

## 🔬 Phase 2: Graph Neural Networks (GraphSAGE)

Phase 2 builds a co-suspicious transaction network and trains a deep Graph Neural Network to capture structural/relational mule accounts.

* **Graph Topology**:
  * **Nodes (Accounts)**: 9,082
  * **Edges (Proximity Links)**: 68,721 (Average Degree: `15.13`)
  * **Layered Edge Rules**: Cosine similarity ($\ge 0.85$) on top 50 SHAP features, tenure proximity (opened within 90 days), and demographic co-occurrence (same occupation & credit score bucket).
* **Node Feature Assembly (74-D Vector)**:
  1. Top 64 SHAP Tabular Features.
  2. 6 Structural Features (Tenure, Active Products, Peer Deviation, Category Probability Encodings, Credit Score).
  3. 2 Temporal Hop Velocity Signature (THVS) Features.
  4. LightGBM transaction risk score.
  5. High Velocity outlier flag.
* **Model Architecture**: 3-layer GraphSAGE (Sample and Aggregate) classifier with dropout (`0.3`) and ReLU activations.
* **Performance**:
  * **Test AUC-ROC**: `0.9999`
  * **Average Precision**: `0.9998`
  * **F1-Score**: `98.80%` (Default `0.5` threshold)

---

## ⚡ Phase 3: Risk Fusion Engine & FastAPI Service

Phase 3 wraps the models in a real-time FastAPI service with composite scoring and decision boundaries.

* **Scoring Formula**:
  $$Composite = 0.35 \times LGBM + 0.40 \times GNN + 0.25 \times CFMS$$
* **Context Boosters (Additive Flags)**:
  * Round transaction amount (e.g. ₹50000): **`+3.0`**
  * New counterparty account: **`+2.0`**
  * Late-night activity (12 AM – 5 AM): **`+4.0`**
  * UPI channel with LightGBM score $> 0.6$: **`+3.0`**
* **Government Alert Registry Mock (CFMS)**: Simulates real-time alerts from the Central Fraud Monitoring System (I4C/FIU-IND) on port `8001`. Features severity multipliers and a freshness decay over 7 days.
* **Caching**: Pre-warmed Redis cache (on port `6379`) with sub-millisecond lookups. Automatically degrades to `InMemoryFeatureStore` if Redis is offline.
* **Endpoints**:
  * `POST /api/v1/score`: Score single transaction context.
  * `POST /api/v1/score/batch`: Concurrent processing for up to 100 transactions.
  * `POST /api/v1/cluster`: Extract co-suspicious node cluster lists.
  * `GET /api/v1/health`: Ingests and reports model/cache statuses.

---

## 📈 Phase 4: Streamlit Analyst Dashboard

Phase 4 delivers a premium analyst UI built in Streamlit featuring a dark mode glassmorphic UI.

1. **Risk Queue**: Monitors accounts, highlighting composite scores, alert flags, and risk tiers (LOW/MEDIUM/HIGH/CRITICAL) and automated actions:
   * **`LOW`** (<40) $\rightarrow$ **`ALLOW`** (Transaction Cleared)
   * **`MEDIUM`** (40–64) $\rightarrow$ **`MONITOR`** (Cleared, flagged for 4h review)
   * **`HIGH`** (65–79) $\rightarrow$ **`HOLD`** (Held for 15m, TMS Alert generated)
   * **`CRITICAL`** ($\ge 80$) $\rightarrow$ **`BLOCK`** (Account frozen, STR report filed)
2. **Account Deep-Dive**: Details account profiles, runs transaction simulation inputs, and draws real-time **SHAP waterfall charts** to explain score attributes.
3. **Network Graph**: Renders a dynamic, interactive visualization of transaction pathways and mule chains using PyVis.
4. **System Monitor**: Visualizes telemetry logs, API response latency, and model specifications.

---

## 🚀 How to Run the Project (Deployment Guide)

### 1. Prerequisite Setup

Ensure Python `3.11` is installed. Run the command to configure the virtual environment and install all requirements:
```bash
# Recreate virtual environment using uv (for high-speed installs)
uv venv --clear --python 3.11
.venv\Scripts\activate   # Windows
source .venv/bin/activate # Linux/Mac

# Install all components
uv pip install -r requirements.txt -r phase3/requirements_phase3.txt -r phase4/requirements_phase4.txt
uv pip install torch torch-geometric
```

### 2. Launching the Project

You can run the demo in two different modes depending on your infrastructure.

#### Mode A: Full Live System (Uvicorn APIs + Streamlit)
Starts the CFMS alert feed registry, the FastAPI risk engine, pre-warms cache, and runs the Analyst Streamlit dashboard:
* **Windows**:
  ```bash
  .\run_demo.bat
  ```
* **Linux / macOS**:
  ```bash
  chmod +x run_demo.sh
  ./run_demo.sh
  ```

#### Mode B: Offline Fallback / Presentation Mode (Dashboard Only)
If you want to run the Streamlit dashboard quickly using pre-baked demo datasets (bypassing the model endpoints and Redis):
* **Windows**:
  ```bash
  .\run_demo_offline.bat
  ```
* **Linux / macOS**:
  ```bash
  chmod +x run_demo_offline.sh
  ./run_demo_offline.sh
  ```

Once launched, access the dashboard at: **[http://localhost:8501](http://localhost:8501)**

---

## 🧪 Running Automated Tests

Run the full suite of backend fusion logic, endpoints, and latency benchmark tests using `pytest`:
```bash
# Run all tests
pytest

# Run specific test suites
pytest phase3/tests/test_fusion.py -v         # Fusion & Context boosters
pytest phase3/tests/test_endpoints.py -v      # FastAPI HTTP endpoints
pytest phase3/tests/test_latency.py -v -s     # P99 Latency benchmark (<150ms constraint)
```

---

## 📦 Project Structure

```
FraudGraphShield/
├── phase1/                  # Tabular Pipeline (LightGBM)
│   ├── models/              # Preprocessors & lightgbm weights
│   ├── preprocessor.py      # Preserving preprocessing transformer
│   └── train.py             # Preprocessing & training pipeline
├── phase2/                  # Graph Neural Networks (GraphSAGE)
│   ├── models/              # PyTorch model weights & PyG graph states
│   ├── gnn_model.py         # GraphSAGE architecture
│   ├── graph_builder.py     # Edges similarity building
│   └── mule_detector.py     # Single-node GNN forward inference wrapper
├── phase3/                  # FastAPI Risk API Backend
│   ├── api/                 # Endpoints routes & model validations
│   ├── core/                # Risk Fusion, Actions, & CFMS Mock registry
│   ├── docker/              # Dockerfiles & Compose files
│   ├── requirements_phase3.txt
│   └── warm_cache.py        # Redis pre-populate script
├── phase4/                  # User Interface Dashboard (Streamlit)
│   ├── dashboard/           # Pages (Risk Queue, Deep Dive, Network Graph, Monitor)
│   │   ├── app.py           # Dashboard Entry
│   │   ├── api_client.py    # FastAPI endpoints connection client
│   │   └── demo_data.py     # Pre-baked fallback data
│   └── requirements_phase4.txt
├── run_demo.bat             # Batch launcher (Live Mode)
├── run_demo_offline.bat     # Batch launcher (Offline Mode)
├── requirements.txt         # Core tabular packages
└── README.md                # Master Documentation (This file)
```
