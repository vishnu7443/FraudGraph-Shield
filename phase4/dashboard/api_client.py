# phase4/dashboard/api_client.py
#
# Client module that wraps Phase 3 FastAPI scoring endpoints.
# Incorporates automated fallback to demo_data.py if backend is unreachable.

# pyrefly: ignore [missing-import]
import httpx
import streamlit as st
import os
import time
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
        headers = {}
        if "jwt_token" in st.session_state and st.session_state["jwt_token"]:
            headers["Authorization"] = f"Bearer {st.session_state['jwt_token']}"
        resp = httpx.get(f"{API_BASE}{endpoint}", params=params, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        if "api_fallback" in st.session_state:
            st.session_state["api_fallback"] = False
        return resp.json()
    except Exception as e:
        st.session_state["api_fallback"] = True
        return None

def _post(endpoint: str, payload: dict) -> Optional[Dict]:
    try:
        headers = {}
        if "jwt_token" in st.session_state and st.session_state["jwt_token"]:
            headers["Authorization"] = f"Bearer {st.session_state['jwt_token']}"
        resp = httpx.post(f"{API_BASE}{endpoint}", json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        if "api_fallback" in st.session_state:
            st.session_state["api_fallback"] = False
        return resp.json()
    except Exception as e:
        st.session_state["api_fallback"] = True
        return None

def login_api(username: str, password: str) -> Optional[Dict]:
    """Authenticates credentials against the backend scoring API."""
    try:
        payload = {"username": username, "password": password}
        resp = httpx.post(f"{API_BASE}/auth/login", json=payload, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 403 or resp.status_code == 401:
            return {"error_detail": resp.json().get("detail", "Authentication failed")}
        return None
    except Exception as e:
        return {"error_detail": f"Backend connection error: {str(e)}"}

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

DEMO_CRYPTO_ALERTS = [
    {
        "alert_id": "ALT-1242-1718300000",
        "txn_id": "TXN-982736192",
        "account_id": 1242,
        "exchange": "WAZIRX",
        "amount": 75000.0,
        "risk_score": 88.5,
        "severity": "CRITICAL",
        "hold_reason": "Funds exiting to high-risk VDA provider WAZIRX (Manual trigger)",
        "timestamp": "2026-06-14T02:15:30Z",
        "status": "OPEN"
    },
    {
        "alert_id": "ALT-1240-1718301000",
        "txn_id": "TXN-102938475",
        "account_id": 1240,
        "exchange": "COINDCX",
        "amount": 120000.0,
        "risk_score": 92.1,
        "severity": "CRITICAL",
        "hold_reason": "Funds exiting to high-risk VDA provider COINDCX (Manual trigger)",
        "timestamp": "2026-06-14T03:45:00Z",
        "status": "OPEN"
    },
    {
        "alert_id": "ALT-8234-1718302000",
        "txn_id": "TXN-564738291",
        "account_id": 8234,
        "exchange": "BINANCE",
        "amount": 45000.0,
        "risk_score": 68.1,
        "severity": "HIGH",
        "hold_reason": "Funds exiting to high-risk VDA provider BINANCE (Manual trigger)",
        "timestamp": "2026-06-14T04:10:15Z",
        "status": "OPEN"
    },
    {
        "alert_id": "ALT-2198-1718303000",
        "txn_id": "TXN-847362910",
        "account_id": 2198,
        "exchange": "COINSWITCH",
        "amount": 25000.0,
        "risk_score": 47.9,
        "severity": "MEDIUM",
        "hold_reason": "Funds exiting to high-risk VDA provider COINSWITCH (Manual trigger)",
        "timestamp": "2026-06-14T04:30:00Z",
        "status": "OPEN"
    },
    {
        "alert_id": "ALT-6734-1718304000",
        "txn_id": "TXN-382910475",
        "account_id": 6734,
        "exchange": "ZEBPAY",
        "amount": 15000.0,
        "risk_score": 44.2,
        "severity": "MEDIUM",
        "hold_reason": "Funds exiting to high-risk VDA provider ZEBPAY (Manual trigger)",
        "timestamp": "2026-06-14T05:05:00Z",
        "status": "RESOLVED"
    }
]

def get_demo_score(account_id: int) -> Dict:
    """Directly fetch demo scores for presentation fallback UI."""
    return _safe_get_score(account_id)

def get_crypto_alerts() -> List[Dict]:
    """Retrieves crypto exit detection alerts from backend or falls back to demo data."""
    if st.session_state.get("use_demo"):
        return DEMO_CRYPTO_ALERTS.copy()
        
    resp = _get("/crypto-alerts")
    if resp is not None:
        return resp
        
    return DEMO_CRYPTO_ALERTS.copy()


def _get_mock_vault_profile(hashed_id: str) -> Dict:
    """Generates mock profile and alert history data when in offline / demo mode."""
    import hashlib
    # Match standard demo account IDs
    h1247 = hashlib.sha256(b"1247").hexdigest()
    h3891 = hashlib.sha256(b"3891").hexdigest()
    
    if hashed_id == h1247 or hashed_id == "1247" or hashed_id == "abc123":
        return {
            "profile": {
                "account_id": 1247,
                "hashed_id": h1247,
                "name": "Arjun Mehta",
                "phone": "+91 98765 43210",
                "pan": "BVPPM7812K",
                "email": "arjun.mehta@outlook.com",
                "created_at": "2025-01-15T10:30:00Z"
            },
            "summary": {
                "total_alerts": 3,
                "highest_risk": 88.5,
                "last_alert": "2026-06-14"
            },
            "alerts": [
                {
                    "alert_id": "VALT-1718300000-1247",
                    "hashed_id": h1247,
                    "risk_score": 88.5,
                    "alert_type": "FUSION_ENGINE_ALERT",
                    "category": "Transaction Risk",
                    "source": "Fusion Engine",
                    "notes": "Automated risk threshold breach: score=88.5, tier=HIGH",
                    "created_at": "2026-06-14T02:15:30Z"
                },
                {
                    "alert_id": "VALT-1718200000-1247",
                    "hashed_id": h1247,
                    "risk_score": 75.2,
                    "alert_type": "CRYPTO_EXIT",
                    "category": "Crypto Risk",
                    "source": "Crypto Detector",
                    "notes": "Funds routing to high-risk VDA exchange WazirX",
                    "created_at": "2026-06-13T18:40:00Z"
                },
                {
                    "alert_id": "VALT-1718100000-1247",
                    "hashed_id": h1247,
                    "risk_score": 62.0,
                    "alert_type": "MULE_ACCOUNT",
                    "category": "Identity Risk",
                    "source": "Manual Investigator",
                    "notes": "Flagged during physical address verification run",
                    "created_at": "2026-06-12T11:15:00Z"
                }
            ]
        }
    elif hashed_id == h3891 or hashed_id == "3891":
        return {
            "profile": {
                "account_id": 3891,
                "hashed_id": h3891,
                "name": "Priya Sharma",
                "phone": "+91 91234 56789",
                "pan": "APOPS2941L",
                "email": "priya.sharma@gmail.com",
                "created_at": "2025-03-22T08:12:00Z"
            },
            "summary": {
                "total_alerts": 1,
                "highest_risk": 45.0,
                "last_alert": "2026-06-10"
            },
            "alerts": [
                {
                    "alert_id": "VALT-1718000000-3891",
                    "hashed_id": h3891,
                    "risk_score": 45.0,
                    "alert_type": "SUSPICIOUS_PAYEE",
                    "category": "Network Risk",
                    "source": "Fusion Engine",
                    "notes": "Frequent small round-amount UPI transfers to unverified numbers",
                    "created_at": "2026-06-10T14:22:00Z"
                }
            ]
        }
    else:
        # Default fallback for arbitrary account hashes
        cleaned_hash = hashed_id if len(hashed_id) > 10 else f"HASH-{hashed_id}-DEMO"
        return {
            "profile": {
                "account_id": 5042,
                "hashed_id": cleaned_hash,
                "name": "Vikram Singh",
                "phone": "+91 98888 77777",
                "pan": "AHYPT1982A",
                "email": "vikram.singh@yahoo.com",
                "created_at": "2025-05-18T16:00:00Z"
            },
            "summary": {
                "total_alerts": 0,
                "highest_risk": 0.0,
                "last_alert": "NEVER"
            },
            "alerts": []
        }


def get_vault_profile(hashed_id: str) -> Optional[Dict]:
    """Retrieves vault account profile details, summary, and alert history."""
    if st.session_state.get("use_demo"):
        return _get_mock_vault_profile(hashed_id)
        
    resp = _get(f"/vault/account/{hashed_id}")
    if resp is not None:
        return resp
        
    return _get_mock_vault_profile(hashed_id)


def create_vault_alert(hashed_id: str, risk_score: float, alert_type: str, category: str, source: str, notes: str = "") -> Optional[Dict]:
    """Creates a fraud alert in the secure vault."""
    import time
    payload = {
        "hashed_id": hashed_id,
        "risk_score": risk_score,
        "alert_type": alert_type,
        "category": category,
        "source": source,
        "notes": notes
    }
    if st.session_state.get("use_demo"):
        # Save alert dynamically in mock session state to show update feedback
        if "mock_alerts" not in st.session_state:
            st.session_state["mock_alerts"] = {}
        if hashed_id not in st.session_state["mock_alerts"]:
            st.session_state["mock_alerts"][hashed_id] = []
            
        mock_id = f"VALT-{int(time.time())}-{hashed_id[:8]}"
        new_alert = {
            "alert_id": mock_id,
            "hashed_id": hashed_id,
            "risk_score": risk_score,
            "alert_type": alert_type,
            "category": category,
            "source": source,
            "notes": notes,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        st.session_state["mock_alerts"][hashed_id].insert(0, new_alert)
        return {"success": True, "alert_id": mock_id}
        
    resp = _post("/vault/alert", payload)
    if resp is not None:
        return resp
        
    return {"success": True, "alert_id": f"MOCK-{int(time.time())}"}


def get_vault_alerts(hashed_id: str) -> List[Dict]:
    """Retrieves only alert log history for an account hash."""
    if st.session_state.get("use_demo"):
        profile_data = _get_mock_vault_profile(hashed_id)
        base_alerts = profile_data.get("alerts", [])
        dyn_alerts = st.session_state.get("mock_alerts", {}).get(hashed_id, [])
        return dyn_alerts + base_alerts
        
    resp = _get(f"/vault/alerts/{hashed_id}")
    if resp is not None:
        return resp
        
    return _get_mock_vault_profile(hashed_id).get("alerts", [])


def require_login():
    """
    Blocks page execution using st.stop() if authentication is missing or invalid.
    Renders a unified glassmorphic Analyst Login panel.
    """
    # Check if token exists
    if "jwt_token" in st.session_state and st.session_state["jwt_token"]:
        # Logged in. Display user badge in sidebar.
        with st.sidebar:
            st.sidebar.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 12px; margin-bottom: 15px;">
                <p style="margin: 0; font-size: 10px; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 0.5px;">Logged In As</p>
                <h4 style="margin: 3px 0; color: #ffffff; font-family:'Outfit', sans-serif;">{st.session_state.get('username', 'User')}</h4>
                <p style="margin: 0; font-size: 11px; color: #10B981; font-weight: 700; text-transform: uppercase;">Role: {st.session_state.get('role', 'analyst')}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.sidebar.button("Logout 🔓", key="auth_logout_btn", use_container_width=True):
                st.session_state["jwt_token"] = None
                st.session_state["username"] = None
                st.session_state["role"] = None
                st.rerun()
        return True

    # Otherwise show premium login card
    st.markdown("""
        <style>
            .login-container {
                max-width: 480px;
                margin: 50px auto 20px auto;
                padding: 35px;
                background: rgba(30, 41, 59, 0.45) !important;
                border: 1px solid rgba(255, 255, 255, 0.08) !important;
                border-radius: 16px !important;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5) !important;
                backdrop-filter: blur(12px) !important;
                -webkit-backdrop-filter: blur(12px) !important;
                text-align: center;
            }
            .login-title {
                font-family: 'Outfit', sans-serif;
                font-size: 26px;
                font-weight: 800;
                color: #FFFFFF;
                margin-bottom: 5px;
            }
            .stButton>button {
                background-color: #2563EB !important;
                color: white !important;
                border-radius: 8px !important;
                border: none !important;
                font-weight: 600 !important;
                padding: 10px 20px !important;
            }
            .stButton>button:hover {
                background-color: #1D4ED8 !important;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
            }
        </style>
        
        <div class="login-container">
            <div class="login-title">🛡️ FraudGraph Shield Gateway</div>
            <p style="color: rgba(255,255,255,0.6); margin-bottom: 15px; font-size:14px;">Investigator & Administrator Authentication Required</p>
        </div>
    """, unsafe_allow_html=True)

    with st.container():
        col_pad1, col_form, col_pad2 = st.columns([1, 2, 1])
        with col_form:
            with st.form("auth_login_form"):
                username = st.text_input("Username", value="analyst", placeholder="e.g. analyst or admin")
                password = st.text_input("Password", value="analyst_shield_2026" if username == "analyst" else "", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Authenticate Access Key", use_container_width=True)

            if submitted:
                u_clean = username.lower().strip()
                if st.session_state.get("use_demo", True):
                    # Offline demo mode validation
                    if u_clean == "analyst" and password == "analyst_shield_2026":
                        st.session_state["jwt_token"] = "mock_analyst_token_2026"
                        st.session_state["username"] = "analyst"
                        st.session_state["role"] = "analyst"
                        st.success("Demo Mode: Authenticated successfully!")
                        time.sleep(0.5)
                        st.rerun()
                    elif u_clean == "admin" and password == "admin_shield_2026":
                        st.session_state["jwt_token"] = "mock_admin_token_2026"
                        st.session_state["username"] = "admin"
                        st.session_state["role"] = "admin"
                        st.success("Demo Mode: Authenticated as Admin successfully!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid credentials (Demo Mode). Try: analyst / analyst_shield_2026")
                else:
                    # Live Mode backend validation
                    res = login_api(u_clean, password)
                    if res and "access_token" in res:
                        st.session_state["jwt_token"] = res["access_token"]
                        st.session_state["username"] = res["username"]
                        st.session_state["role"] = res["role"]
                        st.success("Authenticated successfully!")
                        time.sleep(0.5)
                        st.rerun()
                    elif res and "error_detail" in res:
                        st.error(res["error_detail"])
                    else:
                        st.error("Invalid username or password.")

    st.stop()


def _client_calculate_hash(index, timestamp, action, username, role, endpoint, hashed_id, prev_hash) -> str:
    import hashlib
    safe_hashed_id = hashed_id or ""
    data_str = f"{index}|{timestamp}|{action}|{username}|{role}|{endpoint}|{safe_hashed_id}|{prev_hash}"
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

def _get_mock_ledger() -> List[Dict]:
    if "mock_ledger" not in st.session_state:
        t1 = "2026-06-16 10:00:15"
        t2 = "2026-06-16 10:15:30"
        t3 = "2026-06-16 10:45:10"
        
        g_prev = "0000000000000000000000000000000000000000000000000000000000000000"
        
        h1 = _client_calculate_hash(1, t1, "INVESTIGATOR LOOKUP", "analyst", "analyst", "/vault/account", "f94d2a4c64b63897b2f671c61b17b6dc196a0cc012bd84092b3a0cc309b8c2e6", g_prev)
        h2 = _client_calculate_hash(2, t2, "PROFILE CREATED", "admin", "admin", "/vault/account", "abc123xyz8b63897b2f671c61b17b6dc196a0cc012bd84092b3a0cc309b8c2e6", h1)
        h3 = _client_calculate_hash(3, t3, "ALERT CREATED", "analyst", "analyst", "/vault/alert", "f94d2a4c64b63897b2f671c61b17b6dc196a0cc012bd84092b3a0cc309b8c2e6", h2)
        
        st.session_state["mock_ledger"] = [
            {"log_index": 1, "timestamp": t1, "action": "INVESTIGATOR LOOKUP", "username": "analyst", "role": "analyst", "endpoint": "/vault/account", "hashed_id": "f94d2a4c64b63897b2f671c61b17b6dc196a0cc012bd84092b3a0cc309b8c2e6", "previous_hash": g_prev, "current_hash": h1},
            {"log_index": 2, "timestamp": t2, "action": "PROFILE CREATED", "username": "admin", "role": "admin", "endpoint": "/vault/account", "hashed_id": "abc123xyz8b63897b2f671c61b17b6dc196a0cc012bd84092b3a0cc309b8c2e6", "previous_hash": h1, "current_hash": h2},
            {"log_index": 3, "timestamp": t3, "action": "ALERT CREATED", "username": "analyst", "role": "analyst", "endpoint": "/vault/alert", "hashed_id": "f94d2a4c64b63897b2f671c61b17b6dc196a0cc012bd84092b3a0cc309b8c2e6", "previous_hash": h2, "current_hash": h3}
        ]
    return st.session_state["mock_ledger"]

def _verify_mock_ledger() -> Dict:
    ledger = _get_mock_ledger()
    expected_prev = "0000000000000000000000000000000000000000000000000000000000000000"
    for log in ledger:
        if log["previous_hash"] != expected_prev:
            return {
                "verified": False,
                "tampered_index": log["log_index"],
                "reason": "Previous hash link broken (link mismatch)",
                "expected": expected_prev,
                "found": log["previous_hash"],
                "record": log
            }
        calculated = _client_calculate_hash(
            log["log_index"], log["timestamp"], log["action"], log["username"], log["role"], log["endpoint"], log["hashed_id"], log["previous_hash"]
        )
        if log["current_hash"] != calculated:
            return {
                "verified": False,
                "tampered_index": log["log_index"],
                "reason": "Log entry fields modified (content altered)",
                "expected": calculated,
                "found": log["current_hash"],
                "record": log
            }
        expected_prev = log["current_hash"]
    return {"verified": True, "total_records": len(ledger), "message": f"Cryptographic integrity verified across all {len(ledger)} entries."}

def get_audit_logs() -> List[Dict]:
    """Retrieves all cryptographic audit logs from backend or mock store."""
    if st.session_state.get("use_demo", True):
        return _get_mock_ledger()
        
    res = _get("/audit/logs")
    if res is not None:
        return res
    return _get_mock_ledger()

def verify_audit_chain() -> Dict:
    """Verifies cryptographic audit log integrity."""
    if st.session_state.get("use_demo", True):
        return _verify_mock_ledger()
        
    res = _get("/audit/verify")
    if res is not None:
        return res
    return _verify_mock_ledger()

def simulate_audit_tampering(log_index: int) -> Dict:
    """Simulates log tampering by modifying a username field inside a log record."""
    if st.session_state.get("use_demo", True):
        ledger = _get_mock_ledger()
        for log in ledger:
            if log["log_index"] == log_index:
                log["username"] = "malicious_injected_user"
                return {
                    "success": True, 
                    "message": f"Simulated tampering on record #{log_index} (Demo Mode).",
                    "details": {"log_index": log_index, "original_username": "analyst" if log_index != 2 else "admin", "tampered_username": "malicious_injected_user"}
                }
        return {"success": False, "message": "Log index not found."}
        
    res = _post("/audit/simulate-tamper", {"log_index": log_index, "tampered_username": "malicious_injected_user"})
    if res is not None:
        return res
        
    # fallback
    ledger = _get_mock_ledger()
    for log in ledger:
        if log["log_index"] == log_index:
            log["username"] = "malicious_injected_user"
            return {"success": True, "message": f"Fallback: Simulated tampering on record #{log_index}."}
    return {"success": False}




