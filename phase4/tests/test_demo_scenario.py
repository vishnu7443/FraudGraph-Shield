# phase4/tests/test_demo_scenario.py
#
# Integration and scenario verification test. Simulates an analyst walking through
# the IIT Hyderabad demo scenario (low, medium, high, and critical risk accounts).

import pytest
from phase4.dashboard.demo_data import DEMO_QUEUE, DEMO_METADATA, DEMO_SCORES
from phase4.dashboard import api_client

def test_demo_scenario_data_integrity():
    """Verify that demo queue matches demo metadata and pre-baked scores."""
    # Check that all accounts in DEMO_QUEUE have metadata and score definitions
    for alert in DEMO_QUEUE:
        acc_id = alert["account_id"]
        # Allow child nodes to be mapped to their root cluster parents
        mapped_id = 1001 if acc_id in [1002, 1003, 1004, 1005] else (3003 if acc_id in [3004, 3005] else acc_id)
        assert mapped_id in DEMO_METADATA or acc_id in DEMO_METADATA
        assert mapped_id in DEMO_SCORES or acc_id in DEMO_SCORES

def test_demo_scenario_endpoints_fallback():
    """Test that all scenario endpoints behave correctly in offline fallback mode."""
    # Ensure health_check returns unreachable mock format
    health = api_client.health_check()
    assert health["is_mock"] is True
    assert health["status"] == "unreachable"
    
    # Check score fallback for each key demo account
    for acc_id in [1001, 2002, 3003, 4004]:
        score_info = api_client.score_transaction(acc_id, 10000, "UPI", 12)
        assert score_info["account_id"] == acc_id
        assert score_info["is_mock"] is True
        
        # Verify action thresholds align with expected tier allocations
        if score_info["composite_score"] >= 80.0:
            assert score_info["risk_tier"] == "CRITICAL"
            assert score_info["automated_action"] == "BLOCK"
        elif score_info["composite_score"] >= 65.0:
            assert score_info["risk_tier"] == "HIGH"
            assert score_info["automated_action"] == "HOLD"
        elif score_info["composite_score"] >= 40.0:
            assert score_info["risk_tier"] == "MEDIUM"
            assert score_info["automated_action"] == "MONITOR"
        else:
            assert score_info["risk_tier"] == "LOW"
            assert score_info["automated_action"] == "ALLOW"

def test_demo_scenario_network_clusters():
    """Test retrieving GNN mule clustering structures in offline fallback mode."""
    # Account 1001 (critical) must have a relay chain flagged
    cluster_1001 = api_client.get_cluster(1001)
    assert cluster_1001["root_account_id"] == 1001
    assert cluster_1001["relay_chain_detected"] is True
    assert len(cluster_1001["cluster_nodes"]) == 5
    assert len(cluster_1001["cluster_edges"]) == 4
    
    # Check that the edges connect the relay chain (1001 -> 1002 -> 1003)
    edges = cluster_1001["cluster_edges"]
    connections = {(e["source"], e["target"]) for e in edges}
    assert (1001, 1002) in connections
    assert (1002, 1003) in connections
