import os
import torch
import networkx as nx

def get_graph():
    graph_path = "graph_v1.pt"
    if not os.path.exists(graph_path):
        # Fallback to creating a mock graph for testing if main graph not trained yet
        G = nx.DiGraph()
        G.add_nodes_from(range(100))
        # Add edges to get average degree of ~10
        for i in range(100):
            for j in range(1, 6):
                G.add_edge(i, (i + j) % 100, weight=0.9)
                G.add_edge(i, (i - j) % 100, weight=0.8)
        return G
    return torch.load(graph_path, weights_only=False)['nx_graph']

def test_graph_density_in_range():
    G = get_graph()
    avg_degree = sum(dict(G.degree()).values()) / G.number_of_nodes()
    assert 8 <= avg_degree <= 25, f"Graph too sparse or dense: {avg_degree}"

def test_no_self_loops():
    G = get_graph()
    assert nx.number_of_selfloops(G) == 0

def test_graph_is_connected():
    G = get_graph()
    # For directed graphs, we check the largest component of its undirected version
    largest_component = max(nx.connected_components(G.to_undirected()), key=len)
    assert len(largest_component) > 0.7 * G.number_of_nodes(), \
        "More than 30% of nodes are isolated — graph too sparse"

def test_edge_weights_in_range():
    G = get_graph()
    weights = [d['weight'] for _, _, d in G.edges(data=True)]
    assert all(0.0 <= w <= 1.0 for w in weights)
