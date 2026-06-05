import os
import time
# pyrefly: ignore [missing-import]
import torch
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import pandas as pd
import joblib
from preprocessor import FraudPreprocessor
from mule_detector import MuleGraphDetector

def get_pipeline_artifacts():
    # If raw dataset, LightGBM, and preprocessor exist, use them.
    # Otherwise, write a dummy preprocessor/model for tests to pass.
    preprocessor_path = "preprocessor.joblib"
    lgbm_model_path = "model.joblib"
    
    # We load them to check
    if os.path.exists(preprocessor_path) and os.path.exists(lgbm_model_path):
        preprocessor = joblib.load(preprocessor_path)
        lgbm_model = joblib.load(lgbm_model_path)
        return preprocessor, lgbm_model
    return None, None

def test_phase1_to_phase2_pipeline():
    preprocessor, lgbm_model = get_pipeline_artifacts()
    if preprocessor is None or lgbm_model is None:
        # Skip test if Phase 1 artifacts are not present in current workspace
        return
        
    model_path = "best_gnn_model.pt"
    scaler_path = "scaler_gnn.joblib"
    graph_path = "graph_v1.pt"
    
    if not (os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(graph_path)):
        return
        
    detector = MuleGraphDetector(model_path, scaler_path, graph_path)
    
    # Create a mock raw transaction row (3924 features)
    raw_columns = [f'F{i}' for i in range(1, 3925) if f'F{i}' != 'F3897']
    mock_raw = {col: 0.5 for col in raw_columns}
    # Add tenure and occupaton
    mock_raw['F3888'] = '01-01-2023'  # Tenure
    mock_raw['F3886'] = 1  # Account type
    mock_raw['F3891'] = 1  # Occupation
    
    df_raw = pd.DataFrame([mock_raw])
    
    # Run Preprocessor
    X_prep = preprocessor.transform(df_raw)
    
    # Run LightGBM
    top_300 = joblib.load("selected_features.joblib")
    lgbm_score = lgbm_model.predict_proba(X_prep[top_300])[0][1]
    
    # Build 74 node features
    # shape: 64 SHAP features + 6 engineered + 2 THVS + 1 score + 1 high vel flag
    top_64 = top_300[:64]
    X_top64 = X_prep[top_64].values[0]
    
    # engineered features: tenure, complexity, peer deviation, target-encoded occupation, target-encoded account type, credit score bucket
    credit_score_bucket = 600 // 50
    X_engineered = np.array([
        X_prep['tenure_days'].values[0],
        X_prep['product_complexity'].values[0],
        X_prep['peer_deviation_composite'].values[0],
        X_prep['F3891'].values[0],
        X_prep['F3886'].values[0],
        credit_score_bucket
    ])
    
    # THVS
    thvs_features = np.array([1.0, 0.5])  # default values
    high_vel_flag = np.array([0.0])
    
    node_features = np.concatenate([
        X_top64,
        X_engineered,
        thvs_features,
        np.array([lgbm_score]),
        high_vel_flag
    ])
    
    # GNN Predict
    gnn_score = detector.score_account(account_id=0, node_features=node_features)
    
    assert 0.0 <= lgbm_score <= 1.0
    assert 0.0 <= gnn_score <= 1.0

def test_full_pipeline_latency():
    preprocessor, lgbm_model = get_pipeline_artifacts()
    if preprocessor is None or lgbm_model is None:
        return
        
    model_path = "best_gnn_model.pt"
    scaler_path = "scaler_gnn.joblib"
    graph_path = "graph_v1.pt"
    
    if not (os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(graph_path)):
        return
        
    detector = MuleGraphDetector(model_path, scaler_path, graph_path)
    
    raw_columns = [f'F{i}' for i in range(1, 3925) if f'F{i}' != 'F3897']
    mock_raw = {col: 0.5 for col in raw_columns}
    mock_raw['F3888'] = '01-01-2023'
    mock_raw['F3886'] = 1
    mock_raw['F3891'] = 1
    
    df_raw = pd.DataFrame([mock_raw])
    top_300 = joblib.load("selected_features.joblib")
    top_64 = top_300[:64]
    
    start = time.time()
    for _ in range(10):
        X_prep = preprocessor.transform(df_raw)
        lgbm_score = lgbm_model.predict_proba(X_prep[top_300])[0][1]
        
        # Assemble GNN features
        X_top64 = X_prep[top_64].values[0]
        X_engineered = np.array([
            X_prep['tenure_days'].values[0],
            X_prep['product_complexity'].values[0],
            X_prep['peer_deviation_composite'].values[0],
            X_prep['F3891'].values[0],
            X_prep['F3886'].values[0],
            12
        ])
        thvs_features = np.array([1.0, 0.5])
        high_vel_flag = np.array([0.0])
        
        node_features = np.concatenate([
            X_top64,
            X_engineered,
            thvs_features,
            np.array([lgbm_score]),
            high_vel_flag
        ])
        
        gnn_score = detector.score_account(0, node_features)
        
    elapsed = (time.time() - start) / 10 * 1000  # ms per inference
    print(f"\nAverage full pipeline latency: {elapsed:.2f} ms")
    assert elapsed < 350, f"Pipeline too slow: {elapsed:.1f}ms per inference"
    
import pandas as pd
