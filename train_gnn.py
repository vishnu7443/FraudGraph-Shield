import os
# pyrefly: ignore [missing-import]
import torch
# pyrefly: ignore [missing-import]
import torch.nn.functional as F
# pyrefly: ignore [missing-import]
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import networkx as nx
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    confusion_matrix, precision_recall_curve, average_precision_score
)
from gnn_model import GraphSAGEModel
from graph_builder import build_account_graph

def stratified_node_split(labels, split_ratios):
    """
    Split nodes into train, validation, and test masks stratified by label.
    split_ratios: list of floats [train, val, test] summing to 1.0.
    """
    labels_flat = np.squeeze(labels)
    N = len(labels_flat)
    indices = np.arange(N)
    
    # First, split train and temp (val+test)
    train_idx, temp_idx = train_test_split(
        indices, test_size=split_ratios[1] + split_ratios[2],
        stratify=labels_flat, random_state=42
    )
    
    # Next, split temp into val and test
    val_ratio_in_temp = split_ratios[1] / (split_ratios[1] + split_ratios[2])
    val_idx, test_idx = train_test_split(
        temp_idx, test_size=1.0 - val_ratio_in_temp,
        stratify=labels_flat[temp_idx], random_state=42
    )
    
    # Create masks
    train_mask = torch.zeros(N, dtype=torch.bool)
    val_mask = torch.zeros(N, dtype=torch.bool)
    test_mask = torch.zeros(N, dtype=torch.bool)
    
    train_mask[train_idx] = True
    val_mask[val_idx] = True
    test_mask[test_idx] = True
    
    return train_mask, val_mask, test_mask

def evaluate_auc(model, data, mask):
    model.eval()
    with torch.no_grad():
        probs = model(data.x, data.edge_index, return_logits=False)[mask].numpy()
        labels = data.y[mask].numpy()
    return roc_auc_score(labels, probs)

def main():
    # Set random seeds for deterministic execution
    torch.manual_seed(42)
    np.random.seed(42)
    
    dataset_path = r"d:\down\DataSet.csv"
    selected_features_path = "selected_features.joblib"
    lgbm_model_path = "model.joblib"
    preprocessor_path = "preprocessor.joblib"
    graph_path = "graph_v1.pt"
    
    # 1. Build or Load Graph
    if not os.path.exists(graph_path):
        print(f"Graph artifact not found at '{graph_path}'. Rebuilding graph...")
        G, pyg_data = build_account_graph(dataset_path, selected_features_path, lgbm_model_path, preprocessor_path)
    else:
        print(f"Loading existing graph artifact from '{graph_path}'...")
        graph_dict = torch.load(graph_path, weights_only=False)
        pyg_data = graph_dict['pyg_data']
        G = graph_dict['nx_graph']
        
    # Check graph density
    N = pyg_data.num_nodes
    E = pyg_data.num_edges
    avg_deg = sum(dict(G.degree()).values()) / N
    print(f"Graph loaded: {N} nodes, {E} edges, average degree: {avg_deg:.2f}")
    
    # 2. Node split masks (60/20/20 stratified)
    print("Generating stratified train/validation/test splits...")
    labels = pyg_data.y.numpy()
    train_mask, val_mask, test_mask = stratified_node_split(labels, [0.6, 0.2, 0.2])
    
    # 3. Model initialization
    in_channels = pyg_data.num_node_features
    print(f"Initializing GraphSAGE model (input channels: {in_channels})...")
    model = GraphSAGEModel(in_channels=in_channels, hidden_channels=128, out_channels=1, dropout=0.3)
    
    # Setup optimizer and loss
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=5e-4)
    # Ratio of negatives to positives: 6983/2099 ~= 3.327
    pos_weight = torch.tensor([3.327])
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    
    # 4. Training loop with early stopping
    print("\n--------------------------------------------------")
    print("Training GraphSAGE Model (max 200 epochs with early stopping)...")
    
    best_val_auc = 0
    patience = 20
    patience_counter = 0
    best_model_path = 'best_gnn_model.pt'
    
    for epoch in range(1, 201):
        model.train()
        optimizer.zero_grad()
        # forward pass in logits mode for BCEWithLogitsLoss
        out = model(pyg_data.x, pyg_data.edge_index, return_logits=True)
        loss = criterion(out[train_mask], pyg_data.y[train_mask])
        loss.backward()
        optimizer.step()
        
        # Validate every 5 epochs
        if epoch % 5 == 0:
            val_auc = evaluate_auc(model, pyg_data, val_mask)
            print(f"Epoch {epoch:03d} | Train Loss: {loss.item():.4f} | Val AUC-ROC: {val_auc:.4f}")
            
            if val_auc > best_val_auc:
                best_val_auc = val_auc
                torch.save(model.state_dict(), best_model_path)
                patience_counter = 0
            else:
                patience_counter += 1
                
            if patience_counter >= patience:
                print(f"Early stopping triggered at epoch {epoch} (Validation AUC did not improve for {patience} evaluations)")
                break
                
    # 5. Evaluation on Holdout Test Split
    print("\n--------------------------------------------------")
    print("Evaluating GNN Performance on Test Split...")
    
    # Load best model checkpoint
    model.load_state_dict(torch.load(best_model_path, weights_only=True))
    model.eval()
    
    with torch.no_grad():
        probs = model(pyg_data.x, pyg_data.edge_index, return_logits=False).squeeze().numpy()
        
    test_probs = probs[test_mask]
    test_labels = labels[test_mask].squeeze()
    
    test_auc = roc_auc_score(test_labels, test_probs)
    test_ap = average_precision_score(test_labels, test_probs)
    
    print("\n================ GNN TEST SET METRICS ================")
    print(f"Test AUC-ROC: {test_auc:.4f}")
    print(f"Test Average Precision (AP): {test_ap:.4f}")
    
    # Threshold analysis
    print("\nThreshold Performance Analysis:")
    for thresh in [0.3, 0.4, 0.5, 0.6, 0.7]:
        preds = (test_probs >= thresh).astype(int)
        f1 = f1_score(test_labels, preds)
        prec = precision_score(test_labels, preds)
        rec = recall_score(test_labels, preds)
        print(f"  Threshold {thresh:.1f} -> Precision: {prec:.4f}, Recall: {rec:.4f}, F1: {f1:.4f}")
    print("======================================================\n")
    
    # 6. Extract high-risk clusters and generate visualizations
    print("Generating cluster subgraph visualizations...")
    # Find highest predicted fraud probabilities in the test mask
    test_indices = np.where(test_mask)[0]
    test_probs_mapped = np.zeros(N)
    test_probs_mapped[test_mask] = test_probs
    
    # Sort test nodes by predicted probability
    sorted_test_nodes = test_indices[np.argsort(-test_probs_mapped[test_indices])]
    
    # Top 5 highest risk nodes
    top_5_nodes = sorted_test_nodes[:5]
    os.makedirs("plots", exist_ok=True)
    
    for rank, center_node in enumerate(top_5_nodes, 1):
        # Extract 2-hop neighbors
        hop_nodes = nx.single_source_shortest_path_length(G, center_node, cutoff=2)
        cluster_nodes = list(hop_nodes.keys())
        subgraph = G.subgraph(cluster_nodes)
        
        # Prepare node colors based on predicted mule probabilities (1-prob because RdYlGn: 0=Red, 1=Green)
        colors = [plt.cm.RdYlGn(1.0 - float(probs[node])) for node in cluster_nodes]
        
        plt.figure(figsize=(8, 6))
        pos = nx.spring_layout(subgraph, seed=42)
        
        # Draw GNN node probabilities
        nx.draw_networkx_nodes(subgraph, pos, node_color=colors, node_size=400, edgecolors='black')
        nx.draw_networkx_edges(subgraph, pos, width=1.0, alpha=0.5, edge_color='gray')
        nx.draw_networkx_labels(subgraph, pos, font_size=7, font_family='sans-serif')
        
        plt.title(f"Mule Subgraph Cluster {rank} (Center Node: {center_node})")
        plt.axis('off')
        plt.tight_layout()
        filename = f"plots/cluster_{rank}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Saved cluster visualization plot to '{filename}'")
        
    # Done
    print("\nPhase 2 execution complete! Best GNN model saved to 'best_gnn_model.pt'.")

if __name__ == '__main__':
    main()
