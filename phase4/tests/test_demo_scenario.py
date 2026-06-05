# phase4/tests/test_demo_scenario.py
#
# Integration and scenario verification test. Simulates an analyst walking through
# the IIT Hyderabad demo scenario (low, medium, high, and critical risk accounts).

import pytest
from phase4.dashboard.demo_data import DEMO_RISK_QUEUE, DEMO_SCORES, DEMO_CLUSTERS
from phase4.dashboard import api_client

def test_demo_scenario_data_integrity():
    """Verify that demo queue matches demo metadata and pre-baked scores."""
    # Check that all accounts in DEMO_RISK_QUEUE are present or have lookup paths
    for alert in DEMO_RISK_QUEUE:
        acc_id = alert["account_id"]
        # In fallback mock mode, lookups resolve to DEMO_SCORES or default to first score
        score_info = api_client.get_demo_score(acc_id)
        assert score_info is not None
        assert "composite_score" in score_info

from unittest.mock import patch

def test_demo_scenario_endpoints_fallback():
    """Test that all scenario endpoints behave correctly in offline fallback mode."""
    with patch("phase4.dashboard.api_client._get", return_value=None), \
         patch("phase4.dashboard.api_client._post", return_value=None):
         
        # Ensure health_check returns unreachable mock format
        health = api_client.health_check()
        assert health["is_mock"] is True
        assert health["status"] == "unreachable"
        
        # Check score fallback for each key demo account
        for acc_id in [1247, 3891, 5042, 7234]:
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
    # Account 1247 (critical/medium) must have a cluster mapped
    with patch("phase4.dashboard.api_client._post", return_value=None):
        cluster_1247 = api_client.get_cluster(1247)
        assert cluster_1247["root_account_id"] == 1247
        assert len(cluster_1247["cluster_nodes"]) == 97
        assert cluster_1247["relay_chain_detected"] is True
