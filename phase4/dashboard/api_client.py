# phase4/dashboard/api_client.py
#
# Client module that wraps Phase 3 FastAPI scoring endpoints.
# Incorporates automated fallback to demo_data.py if backend is unreachable.

# pyrefly: ignore [missing-import]
import httpx
# pyrefly: ignore [missing-import]
import streamlit as st
import os
from typing import Optional, Dict, List

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
TIMEOUT = 3.0  # seconds

def check_backend_alive() -> bool:
    """Checks if the FastAPI backend is running."""
    try:
        resp = httpx.get(f"{API_BASE}/health", timeout=1.0)
        return resp.status_code == 200
    except Exception:
        return False

def _get(endpoint: str, params: dict = {}) -> Optional[dict]:
    try:
        resp = httpx.get(f"{API_BASE}{endpoint}", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        if "api_fallback" in st.session_state:
            st.session_state["api_fallback"] = False
        return resp.json()
    except Exception as e:
        st.session_state["api_fallback"] = True
        return None

def _post(endpoint: str, payload: dict) -> Optional[dict]:
    try:
        resp = httpx.post(f"{API_BASE}{endpoint}", json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        if "api_fallback" in st.session_state:
            st.session_state["api_fallback"] = False
        return resp.json()
    except Exception as e:
        st.session_state["api_fallback"] = True
        return None

def health_check() -> dict:
    """Verifies backend API and model lifespan status."""
    result = _get("/health")
    if result:
        return result
    else:
        return {"status": "unreachable", "feature_store": "unknown", "models": "unknown", "is_mock": True}

def score_transaction(account_id: int, amount: float,
                      channel: str, hour: int,
                      is_new_counterparty: bool = False,
                      is_round_amount: bool = False) -> dict:
    """Scores a transaction in real-time or falls back to demo data."""
    payload = {
        "account_id": account_id,
        "transaction_amount": amount,
        "channel": channel,
        "hour_of_day": hour,
        "is_new_counterparty": is_new_counterparty,
        "is_round_amount": is_round_amount
    }
    
    # Try calling backend API
    resp = _post("/score", payload)
    if resp:
        resp["is_mock"] = False
        return resp
        
    # Fallback to pre-baked demo scenario
    st.session_state["api_fallback"] = True
    from phase4.dashboard.demo_data import DEMO_SCORES
    mock_score = DEMO_SCORES.get(account_id, DEMO_SCORES[0]).copy()
    mock_score["account_id"] = account_id
    mock_score["is_mock"] = True
    return mock_score

def get_cluster(account_id: int, hop_depth: int = 2) -> dict:
    """Retrieves cluster network nodes & edges from backend or falls back to demo data."""
    payload = {
        "account_id": account_id,
        "hop_depth": hop_depth
    }
    
    resp = _post("/cluster", payload)
    if resp:
        resp["is_mock"] = False
        return resp
        
    # Fallback to pre-baked demo scenario
    st.session_state["api_fallback"] = True
    from phase4.dashboard.demo_data import DEMO_CLUSTERS
    # Find matching cluster or generate simple mock cluster
    cluster = DEMO_CLUSTERS.get(account_id)
    if not cluster:
        # Fallback dynamic mock cluster
        cluster = {
            "root_account_id": account_id,
            "relay_chain_detected": False,
            "cluster_nodes": [
                {"account_id": account_id, "composite_score": 15.0, "gnn_mule_score": 0.1, "risk_tier": "LOW", "automated_action": "ALLOW"}
            ],
            "cluster_edges": []
        }
    cluster_copy = cluster.copy()
    cluster_copy["is_mock"] = True
    return cluster_copy

def score_batch(requests: list) -> List[dict]:
    """Scores a batch of transactions concurrently or falls back to demo data."""
    resp = _post("/score/batch", {"requests": requests})
    if resp is not None:
        return resp
        
    # Fallback to pre-baked demo scenario
    st.session_state["api_fallback"] = True
    from phase4.dashboard.demo_data import DEMO_SCORES
    results = []
    for req in requests:
        acc_id = req["account_id"]
        mock_score = DEMO_SCORES.get(acc_id, DEMO_SCORES[0]).copy()
        mock_score["account_id"] = acc_id
        mock_score["is_mock"] = True
        results.append(mock_score)
    return results

def get_demo_score(account_id: int) -> dict:
    """Directly fetch demo scores for presentation fallback UI."""
    from phase4.dashboard.demo_data import DEMO_SCORES
    return DEMO_SCORES.get(account_id, DEMO_SCORES[0])
