# phase4/dashboard/api_client.py
#
# Client module that wraps Phase 3 FastAPI scoring endpoints.
# Incorporates automated fallback to demo_data.py if backend is unreachable.

# pyrefly: ignore [missing-import]
import httpx
import streamlit as st
import os
from typing import Optional, Dict, List

# Try importing demo data with package-relative path for pytest,
# and fallback to top-level import for Streamlit runner runtime.
try:
    from phase4.dashboard.demo_data import DEMO_SCORES, DEMO_CLUSTERS
except ModuleNotFoundError:
    try:
        from demo_data import DEMO_SCORES, DEMO_CLUSTERS
    except ModuleNotFoundError:
        # Fallback to direct import in case of other nested paths
        from .demo_data import DEMO_SCORES, DEMO_CLUSTERS

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
TIMEOUT = 3.0  # seconds

def check_backend_alive() -> bool:
    """Checks if the FastAPI backend is running."""
    try:
        resp = httpx.get(f"{API_BASE}/health", timeout=1.0)
        return resp.status_code == 200
    except Exception:
        return False

def _get(endpoint: str, params: dict = {}) -> Optional[Dict]:
    try:
        resp = httpx.get(f"{API_BASE}{endpoint}", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        if "api_fallback" in st.session_state:
            st.session_state["api_fallback"] = False
        return resp.json()
    except Exception as e:
        st.session_state["api_fallback"] = True
        return None

def _post(endpoint: str, payload: dict) -> Optional[Dict]:
    try:
        resp = httpx.post(f"{API_BASE}{endpoint}", json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        if "api_fallback" in st.session_state:
            st.session_state["api_fallback"] = False
        return resp.json()
    except Exception as e:
        st.session_state["api_fallback"] = True
        return None
def _safe_get_score(account_id) -> Dict:
    res = DEMO_SCORES.get(account_id) or DEMO_SCORES.get(str(account_id))
    if not res:
        res = list(DEMO_SCORES.values())[0]
    return res.copy()

def _safe_get_cluster(account_id) -> Dict:
    res = DEMO_CLUSTERS.get(account_id) or DEMO_CLUSTERS.get(str(account_id))
    if not res:
        res = list(DEMO_CLUSTERS.values())[0]
    return res.copy()

def health_check() -> Dict:
    """Verifies backend API and model lifespan status."""
    result = _get("/health")
    if result:
        return result
    else:
        return {"status": "unreachable", "feature_store": "unknown", "models": "unknown", "is_mock": True}

def score_transaction(account_id: int, amount: float,
                      channel: str, hour: int,
                      is_new_counterparty: bool = False,
                      is_round_amount: bool = False,
                      destination_name: Optional[str] = None) -> Dict:
    """Scores a transaction in real-time or falls back to demo data."""
    payload = {
        "account_id": account_id,
        "transaction_amount": amount,
        "channel": channel,
        "hour_of_day": hour,
        "is_new_counterparty": is_new_counterparty,
        "is_round_amount": is_round_amount,
        "destination_name": destination_name
    }
    
    # Try calling backend API
    resp = _post("/score", payload)
    if resp:
        resp["is_mock"] = False
        return resp
        
    # Fallback to pre-baked demo scenario
    st.session_state["api_fallback"] = True
    mock_score = _safe_get_score(account_id)
    mock_score["account_id"] = account_id
    mock_score["is_mock"] = True
    
    # Simulate crypto detection in mock fallback if destination_name matches
    if destination_name:
        dest_upper = destination_name.strip().upper()
        exchanges = ["WAZIRX", "COINDCX", "ZEBPAY", "BINANCE", "COINSWITCH", "BITBNS", "MUDREX"]
        matched_ex = next((ex for ex in exchanges if ex in dest_upper), None)
        if matched_ex:
            mock_score["crypto_detected"] = True
            mock_score["crypto_exchange"] = matched_ex
            mock_score["crypto_confidence"] = 0.95
            
            # Apply mock score boost
            original_score = mock_score.get("composite_score", 50.0)
            if original_score > 40.0:
                mock_score["composite_score"] = min(100.0, original_score + 20.0)
            mock_score["automated_action"] = "HOLD"
            if mock_score["risk_tier"] in ["LOW", "MEDIUM"]:
                mock_score["risk_tier"] = "HIGH"
        else:
            mock_score["crypto_detected"] = False
            mock_score["crypto_exchange"] = None
            mock_score["crypto_confidence"] = 0.0
    else:
        mock_score["crypto_detected"] = False
        mock_score["crypto_exchange"] = None
        mock_score["crypto_confidence"] = 0.0

    return mock_score


def get_crypto_alerts() -> List[Dict]:
    """Fetches list of crypto alerts from backend or returns offline fallback mocks."""
    resp = _get("/crypto-alerts")
    if resp is not None:
        return resp
        
    # Fallback offline mocks
    return [
        {
            "alert_id": "ALT-1247-1723500000",
            "txn_id": "TXN-1247-1723500000",
            "account_id": 1247,
            "exchange": "WAZIRX",
            "amount": 95000.0,
            "risk_score": 91.4,
            "severity": "CRITICAL",
            "hold_reason": "Funds exiting to high-risk VDA provider WAZIRX",
            "timestamp": "2026-06-14T08:00:00Z",
            "status": "OPEN"
        },
        {
            "alert_id": "ALT-3891-1723510000",
            "txn_id": "TXN-3891-1723510000",
            "account_id": 3891,
            "exchange": "COINDCX",
            "amount": 42000.0,
            "risk_score": 78.5,
            "severity": "HIGH",
            "hold_reason": "Funds exiting to high-risk VDA provider COINDCX",
            "timestamp": "2026-06-14T07:12:00Z",
            "status": "OPEN"
        },
        {
            "alert_id": "ALT-5042-1723520000",
            "txn_id": "TXN-5042-1723520000",
            "account_id": 5042,
            "exchange": "ZEBPAY",
            "amount": 12000.0,
            "risk_score": 55.2,
            "severity": "MEDIUM",
            "hold_reason": "Funds exiting to high-risk VDA provider ZEBPAY",
            "timestamp": "2026-06-14T05:30:00Z",
            "status": "RESOLVED"
        }
    ]


def get_cluster(account_id: int, hop_depth: int = 2) -> Dict:
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
    cluster_copy = _safe_get_cluster(account_id)
    cluster_copy["is_mock"] = True
    return cluster_copy

def score_batch(requests: list) -> List[Dict]:
    """Scores a batch of transactions concurrently or falls back to demo data."""
    resp = _post("/score/batch", {"requests": requests})
    if resp is not None:
        return resp
        
    # Fallback to pre-baked demo scenario
    st.session_state["api_fallback"] = True
    results = []
    for req in requests:
        acc_id = req["account_id"]
        mock_score = _safe_get_score(acc_id)
        mock_score["account_id"] = acc_id
        mock_score["is_mock"] = True
        results.append(mock_score)
    return results

def get_demo_score(account_id: int) -> Dict:
    """Directly fetch demo scores for presentation fallback UI."""
    return _safe_get_score(account_id)

