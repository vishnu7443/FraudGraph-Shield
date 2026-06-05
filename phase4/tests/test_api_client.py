# phase4/tests/test_api_client.py
#
# Unit tests for the api_client wrapper. Verifies correct real-time routing and
# graceful fallback to pre-baked demo scores if backend endpoints are down.

import pytest
from unittest.mock import patch, MagicMock
import streamlit as st
import numpy as np

# Mock st.session_state for testing client outside streamlit runner environment
if "api_fallback" not in st.session_state:
    st.session_state["api_fallback"] = False

from phase4.dashboard import api_client

def test_fallback_score_transaction():
    """Test that when API is unreachable, score_transaction falls back to pre-baked data."""
    # Force _post to raise an exception by patching it
    with patch("phase4.dashboard.api_client._post", return_value=None):
        res = api_client.score_transaction(
            account_id=1001,
            amount=50000.0,
            channel="UPI",
            hour=14,
            is_new_counterparty=True,
            is_round_amount=True
        )
        assert res is not None
        assert res["account_id"] == 1001
        assert res["is_mock"] is True
        assert res["composite_score"] == 94.2
        assert res["automated_action"] == "BLOCK"
        assert st.session_state["api_fallback"] is True

def test_successful_api_score():
    """Test that when API returns values, score_transaction routes them correctly."""
    mock_response = {
        "account_id": 1001,
        "composite_score": 45.0,
        "risk_tier": "MEDIUM",
        "automated_action": "MONITOR",
        "lgbm_score": 0.4,
        "gnn_mule_score": 0.5,
        "cfms_alert_active": False,
        "top_shap_factors": [],
        "inference_latency_ms": 12.0
    }
    with patch("phase4.dashboard.api_client._post", return_value=mock_response):
        res = api_client.score_transaction(1001, 20000.0, "UPI", 12)
        assert res is not None
        assert res["account_id"] == 1001
        assert res["is_mock"] is False
        assert res["composite_score"] == 45.0
        assert res["automated_action"] == "MONITOR"

def test_fallback_get_cluster():
    """Test that when API is unreachable, get_cluster falls back to pre-baked clusters."""
    with patch("phase4.dashboard.api_client._post", return_value=None):
        res = api_client.get_cluster(1001)
        assert res is not None
        assert res["root_account_id"] == 1001
        assert res["is_mock"] is True
        assert res["relay_chain_detected"] is True
        assert len(res["cluster_nodes"]) == 5
