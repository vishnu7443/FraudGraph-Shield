# pyrefly: ignore [missing-import]
import torch
# pyrefly: ignore [missing-import]
import joblib
import networkx as nx
# pyrefly: ignore [missing-import]
import numpy as np
from gnn_model import GraphSAGEModel

class MuleGraphDetector:
    def __init__(self, model_path, scaler_path, graph_path):
        # 1. Load model architecture and weights
        self.model = GraphSAGEModel(in_channels=74, hidden_channels=128, out_channels=1)
        self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu'), weights_only=True))
        self.model.eval()
        
        # 2. Load scaler
        self.scaler = joblib.load(scaler_path)
        
        # 3. Load graph structure
        graph_data = torch.load(graph_path, map_location=torch.device('cpu'), weights_only=False)
        if isinstance(graph_data, dict):
            self.pyg_data = graph_data['pyg_data']
            self.nx_graph = graph_data['nx_graph']
        else:
            self.pyg_data = graph_data
            # Build NetworkX DiGraph dynamically if saved as raw PyG Data
            self.nx_graph = nx.DiGraph()
            self.nx_graph.add_nodes_from(range(self.pyg_data.num_nodes))
            edge_index = self.pyg_data.edge_index.numpy()
            edges = [(edge_index[0, i], edge_index[1, i]) for i in range(edge_index.shape[1])]
            self.nx_graph.add_edges_from(edges)

    def score_account(self, account_id, node_features):
        """
        Scores a single account by temporarily replacing its features in the graph 
        and running GraphSAGE forward inference.
        """
        # Standardize features
        features_2d = np.array(node_features).reshape(1, -1)
        scaled_features = self.scaler.transform(features_2d)
        
        # Clone pyg_data to avoid side-effects during scoring
        x_clone = self.pyg_data.x.clone()
        x_clone[account_id] = torch.tensor(scaled_features[0], dtype=torch.float)
        
        # Run inference
        with torch.no_grad():
            probs = self.model(x_clone, self.pyg_data.edge_index, return_logits=False)
            score = float(probs[account_id].item())
            
        return score

    def score_batch(self, account_ids, node_feature_matrix):
        """
        Scores a batch of accounts by temporarily replacing their features in the graph.
        """
        # Standardize feature matrix
        features_2d = np.array(node_feature_matrix)
        scaled_features = self.scaler.transform(features_2d)
        
        # Clone pyg_data features
        x_clone = self.pyg_data.x.clone()
        for idx, acc_id in enumerate(account_ids):
            x_clone[acc_id] = torch.tensor(scaled_features[idx], dtype=torch.float)
            
        # Run inference
        with torch.no_grad():
            probs = self.model(x_clone, self.pyg_data.edge_index, return_logits=False)
            scores = probs[account_ids].squeeze().numpy()
            
        # Ensure returns numpy array even for single elements
        if scores.ndim == 0:
            scores = np.array([scores.item()])
        return scores

    def get_cluster(self, account_id, hop=2):
        """
        Returns a list of account IDs (neighbor node IDs) within the specified hop distance.
        """
        lengths = nx.single_source_shortest_path_length(self.nx_graph, account_id, cutoff=hop)
        # Exclude the node itself
        neighbors = [node for node in lengths.keys() if node != account_id]
        return neighbors

    def save(self, path):
        """
        Saves the MuleGraphDetector state to a file.
        """
        joblib.dump(self, path)
        print(f"Saved MuleGraphDetector to {path}")
        
    @staticmethod
    def load(path):
        """
        Loads the MuleGraphDetector state from a file.
        """
        return joblib.load(path)
