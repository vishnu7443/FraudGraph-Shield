import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import joblib
import os
# pyrefly: ignore [missing-import]
import torch
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
# pyrefly: ignore [missing-import]
from torch_geometric.data import Data
import networkx as nx
from preprocessor import FraudPreprocessor
from thvs import compute_thvs_features_df

def build_account_graph(dataset_path, selected_features_path, lgbm_model_path, preprocessor_path):
    print("==================================================")
    print("FraudGraph Shield - Phase 2: Graph Construction")
    print("==================================================")
    
    import csv
    
    target_col = 'F3897'
    
    # Load Phase 1 artifacts
    print("Loading Phase 1 production artifacts...")
    preprocessor = joblib.load(preprocessor_path)
    lgbm_model = joblib.load(lgbm_model_path)
    top_300 = joblib.load(selected_features_path)
    
    # 1. Pre-compute velocity composite and THVS features row-by-row to save memory
    print("Pre-computing velocity composite and THVS features row-by-row...")
    short_window_indices = [i for i in range(1, 3886) if i % 6 in [1, 2]]
    long_window_indices = [i for i in range(1, 3886) if i % 6 in [5, 0]]
    credit_indices = [i for i in range(1, 3886) if i % 6 in [1, 3, 5]]
    debit_indices = [i for i in range(1, 3886) if i % 6 in [2, 4, 0]]
    all_velocity_indices = set(range(1, 3886))
    
    with open(dataset_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        name_to_idx = {name: idx for idx, name in enumerate(header)}
        
        short_cols_idx = [name_to_idx[f'F{i}'] for i in short_window_indices if f'F{i}' in name_to_idx]
        long_cols_idx = [name_to_idx[f'F{i}'] for i in long_window_indices if f'F{i}' in name_to_idx]
        credit_cols_idx = [name_to_idx[f'F{i}'] for i in credit_indices if f'F{i}' in name_to_idx]
        debit_cols_idx = [name_to_idx[f'F{i}'] for i in debit_indices if f'F{i}' in name_to_idx]
        all_velocity_idx = [name_to_idx[f'F{i}'] for i in all_velocity_indices if f'F{i}' in name_to_idx]
        
        target_idx = name_to_idx.get('F3897', None)
        credit_score_idx = name_to_idx.get('F3896', None)
        
        y_list = []
        credit_score_bucket_list = []
        velocity_composite_list = []
        hop_speed_ratios_list = []
        retention_ratios_list = []
        
        for row in reader:
            val_target = 0.0
            if target_idx is not None and target_idx < len(row):
                try:
                    val_target = float(row[target_idx])
                except ValueError:
                    pass
            y_list.append(1 if val_target > 0 else 0)
            
            val_cs = 600.0
            if credit_score_idx is not None and credit_score_idx < len(row):
                try:
                    val_cs = float(row[credit_score_idx]) if row[credit_score_idx] != "" else 600.0
                except ValueError:
                    pass
            credit_score_bucket_list.append(int(val_cs // 50))
            
            vel_vals = []
            for idx in all_velocity_idx:
                if idx < len(row) and row[idx] != "":
                    try:
                        vel_vals.append(float(row[idx]))
                    except ValueError:
                        pass
                else:
                    vel_vals.append(0.5)
            velocity_composite_list.append(np.mean(vel_vals) if vel_vals else 0.5)
            
            short_vals = []
            for idx in short_cols_idx:
                if idx < len(row) and row[idx] != "":
                    try:
                        val = float(row[idx])
                        if val != 0.5:
                            short_vals.append(val)
                    except ValueError:
                        pass
            short_mean = np.mean(short_vals) if short_vals else 0.5
            
            long_vals = []
            for idx in long_cols_idx:
                if idx < len(row) and row[idx] != "":
                    try:
                        val = float(row[idx])
                        if val != 0.5:
                            long_vals.append(val)
                    except ValueError:
                        pass
            long_mean = np.mean(long_vals) if long_vals else 0.5
            
            hop_ratio = short_mean / (long_mean + 1e-8)
            if not np.isfinite(hop_ratio):
                hop_ratio = 1.0
            hop_speed_ratios_list.append(hop_ratio)
            
            credit_vals = []
            for idx in credit_cols_idx:
                if idx < len(row) and row[idx] != "":
                    try:
                        credit_vals.append(float(row[idx]))
                    except ValueError:
                        pass
            debit_vals = []
            for idx in debit_cols_idx:
                if idx < len(row) and row[idx] != "":
                    try:
                        debit_vals.append(float(row[idx]))
                    except ValueError:
                        pass
            avg_credit = np.mean(credit_vals) if credit_vals else 0.5
            avg_debit = np.mean(debit_vals) if debit_vals else 0.5
            retention = 1.0 - (avg_debit / (avg_credit + 1e-8))
            retention_ratios_list.append(np.clip(retention, 0.0, 1.0))
            
    y = np.array(y_list, dtype=np.int32)
    credit_score_bucket = np.array(credit_score_bucket_list, dtype=np.float32).reshape(-1, 1)
    velocity_composite = np.array(velocity_composite_list, dtype=np.float32)
    thvs_features = np.column_stack([hop_speed_ratios_list, retention_ratios_list]).astype(np.float32)
    
    # 2. Load preprocessor-required columns using standard csv module to avoid pandas C parser memory limits
    print("Loading optimized preprocessor columns using csv module...")
    complexity_cols = [f'F{i}' for i in range(3900, 3925)]
    peer_dev_cols = [f'F{i}' for i in range(3880, 3886)]
    needed_raw = {target_col, 'F3886', 'F3888', 'F3891', 'F3895', 'F3896', 'Unnamed: 0'}
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
            
    use_cols_set = {c for c in needed_raw if c in name_to_idx}
    
    columns_dict = {col: [] for col in use_cols_set}
    
    with open(dataset_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        col_indices = {col: name_to_idx[col] for col in use_cols_set}
        
        str_cols = {'F3886', 'F3888', 'F3891', 'F3892', 'F3893'}
        
        for row in reader:
            for col, idx in col_indices.items():
                val = row[idx]
                if col in str_cols:
                    columns_dict[col].append(val)
                else:
                    if val == "":
                        columns_dict[col].append(np.nan)
                    else:
                        try:
                            columns_dict[col].append(np.float32(val))
                        except ValueError:
                            columns_dict[col].append(val)
                            
    df = pd.DataFrame(columns_dict)
    del columns_dict
    import gc
    gc.collect()
    
    # Ensure plots directory exists
    os.makedirs("plots", exist_ok=True)
    
    # 3. Extract Phase 1 Preprocessed Features
    print("Preprocessing raw data...")
    X_prep = preprocessor.transform(df)
    
    # 4. Compute Phase 1 LGBM scores
    print("Generating LightGBM risk scores...")
    lgbm_scores = lgbm_model.predict_proba(X_prep[top_300])[:, 1].reshape(-1, 1)
    
    # 5. Extract engineered features
    print("Extracting engineered features...")
    tenure = X_prep['tenure_days'].values.reshape(-1, 1)
    complexity = X_prep['product_complexity'].values.reshape(-1, 1)
    peer_dev = X_prep['peer_deviation_composite'].values.reshape(-1, 1)
    
    occ_encoded = X_prep['F3891'].values.reshape(-1, 1)
    acc_encoded = X_prep['F3886'].values.reshape(-1, 1)
    
    X_engineered = np.concatenate([
        tenure, complexity, peer_dev, occ_encoded, acc_encoded, credit_score_bucket
    ], axis=1)
    
    # 6. Extract high velocity flag
    high_vel_thresh = np.percentile(velocity_composite, 75)
    high_vel_flag = (velocity_composite > high_vel_thresh).astype(float).reshape(-1, 1)
    
    # 7. Extract top 64 SHAP features
    top_64_cols = top_300[:64]
    X_top64 = X_prep[top_64_cols].values
    
    # 8. Assemble Node Feature Matrix
    print("Assembling node feature matrix (shape: (9082, 74))...")
    node_features = np.concatenate([
        X_top64,
        X_engineered,
        thvs_features,
        lgbm_scores,
        high_vel_flag
    ], axis=1)
    
    # Normalize node feature matrix
    print("Normalizing node feature matrix...")
    scaler = StandardScaler()
    node_features_normalized = scaler.fit_transform(node_features)
    joblib.dump(scaler, "scaler_gnn.joblib")
    
    # 9. Build Graph Edges (deterministic search)
    print("Building account transaction graph...")
    N = len(df)
    
    # We will perform dynamic thresholding to target average degree between 8 and 25
    top_50_cols = top_300[:50]
    X_top50 = X_prep[top_50_cols].values
    high_velocity_mask = velocity_composite > np.median(velocity_composite)
    
    # Nearest neighbors cosine search (chunked to avoid memory limits)
    print("Fitting NearestNeighbors model for Layer 1 similarity...")
    nn = NearestNeighbors(n_neighbors=15, metric='cosine', n_jobs=1)
    nn.fit(X_top50)
    print("Querying NearestNeighbors in chunks...")
    chunk_size = 500
    distances_list = []
    indices_list = []
    for start_idx in range(0, N, chunk_size):
        end_idx = min(start_idx + chunk_size, N)
        dist_chunk, ind_chunk = nn.kneighbors(X_top50[start_idx:end_idx])
        distances_list.append(dist_chunk)
        indices_list.append(ind_chunk)
    distances = np.concatenate(distances_list, axis=0)
    indices = np.concatenate(indices_list, axis=0)
    
    # Layer 2 & Layer 3 groupings
    print("Computing Layer 2 (Risk & Tenure Proximity) groupings...")
    l2_groups = {}
    for idx in range(N):
        key = (y[idx], df['F3886'].iloc[idx])
        if key not in l2_groups:
            l2_groups[key] = []
        l2_groups[key].append(idx)
        
    print("Computing Layer 3 (CFMS Co-occurrence) groupings...")
    l3_groups = {}
    for idx in range(N):
        if y[idx] == 1:
            key = (df['F3891'].iloc[idx], credit_score_bucket[idx][0])
            if key not in l3_groups:
                l3_groups[key] = []
            l3_groups[key].append(idx)
            
    # Iterate thresholds
    thresholds = [0.85, 0.80, 0.90]
    best_G = None
    best_edges = []
    
    for thresh in thresholds:
        print(f"Testing Layer 1 Cosine Threshold: {thresh:.2f}...")
        edges = []
        
        # Layer 1: Proximity similarity
        for i in range(N):
            for k in range(1, 15):  # index 0 is self
                j = indices[i][k]
                sim = 1.0 - distances[i][k]
                if sim > thresh and high_velocity_mask[i] and high_velocity_mask[j]:
                    edges.append((i, j, sim))
                    
        # Layer 2: Risk and tenure proximity (limit to at most 3 closest neighbors to keep graph sparse and avoid memory error)
        for key, indices_list in l2_groups.items():
            indices_list = sorted(indices_list, key=lambda idx: tenure[idx][0])
            n_g = len(indices_list)
            for i in range(n_g):
                count = 0
                for j in range(i + 1, n_g):
                    if count >= 3:
                        break
                    idx_i = indices_list[i]
                    idx_j = indices_list[j]
                    if tenure[idx_j][0] - tenure[idx_i][0] <= 90:
                        edges.append((idx_i, idx_j, 0.5))
                        count += 1
                    else:
                        break
                        
        # Layer 3: Demographic co-occurrence (limit to at most 3 connections per node to keep graph sparse and avoid memory error)
        for key, indices_list in l3_groups.items():
            n_g = len(indices_list)
            for i in range(n_g):
                idx_i = indices_list[i]
                for step in range(1, min(4, n_g)):
                    idx_j = indices_list[(i + step) % n_g]
                    edges.append((idx_i, idx_j, 0.4))
                        
        # Build DiGraph
        G = nx.DiGraph()
        G.add_nodes_from(range(N))
        G.add_weighted_edges_from(edges)
        
        # Calculate density (average total degree: in-degree + out-degree)
        avg_degree = sum(dict(G.degree()).values()) / N
        print(f"  Graph average degree: {avg_degree:.2f} (edges: {G.number_of_edges()})")
        
        if 8 <= avg_degree <= 25:
            print(f"  Average degree {avg_degree:.2f} is in target range [8, 25]. Selected threshold {thresh:.2f}.")
            best_G = G
            best_edges = edges
            break
        elif best_G is None or (abs(avg_degree - 16.5) < abs(sum(dict(best_G.degree()).values())/N - 16.5)):
            best_G = G
            best_edges = edges
            
    # Statistics logging
    E = best_G.number_of_edges()
    avg_deg = sum(dict(best_G.degree()).values()) / N
    clustering = nx.average_clustering(best_G.to_undirected())
    
    print("\n================ GRAPH STATISTICS ================")
    print(f"Nodes (Accounts): {N}")
    print(f"Edges (Proximity Links): {E}")
    print(f"Average Total Degree: {avg_deg:.4f}")
    print(f"Average Clustering Coefficient: {clustering:.4f}")
    print("==================================================\n")
    
    # Export to PyTorch Geometric Data format
    edge_index = []
    edge_attr = []
    for u, v, data in best_G.edges(data=True):
        edge_index.append([u, v])
        edge_attr.append(data.get('weight', 1.0))
        
    edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
    edge_attr = torch.tensor(edge_attr, dtype=torch.float)
    x = torch.tensor(node_features_normalized, dtype=torch.float)
    y_tensor = torch.tensor(y, dtype=torch.float).unsqueeze(1)
    
    pyg_data = Data(x=x, y=y_tensor, edge_index=edge_index, edge_attr=edge_attr)
    
    # Save graph artifacts
    graph_path = "graph_v1.pt"
    torch.save({
        'pyg_data': pyg_data,
        'nx_graph': best_G
    }, graph_path)
    print(f"Saved NetworkX and PyG graph artifacts successfully to '{graph_path}'!")
    
    return best_G, pyg_data

if __name__ == '__main__':
    dataset_path = r"d:\down\DataSet.csv"
    selected_features_path = "selected_features.joblib"
    lgbm_model_path = "model.joblib"
    preprocessor_path = "preprocessor.joblib"
    
    if os.path.exists(dataset_path):
        build_account_graph(dataset_path, selected_features_path, lgbm_model_path, preprocessor_path)
    else:
        print(f"Dataset path {dataset_path} does not exist.")
