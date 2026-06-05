import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import numpy as np

# Mock the entire lifespan models loading
@pytest.fixture(scope="module", autouse=True)
def mock_app_state():
    with patch('phase3.api.main.RiskFusionEngine') as mock_engine_cls, \
         patch('phase3.api.main.InMemoryFeatureStore') as mock_store_cls, \
         patch('phase3.api.main.ActionEngine') as mock_action_cls:
         
        # Set up mock instances
        mock_engine = MagicMock()
        mock_engine.score_transaction = AsyncMock(return_value={
            "account_id": 100,
            "composite_score": 45.2,
            "risk_tier": "MEDIUM",
            "automated_action": "MONITOR",
            "lgbm_score": 0.35,
            "gnn_mule_score": 0.55,
            "cfms_alert_active": False,
            "cfms_alert_age_hours": None,
            "top_shap_factors": [],
            "inference_latency_ms": 1.25,
            "model_version": "v1.0.0"
        })
        
        # Mock detector inside engine
        mock_detector = MagicMock()
        mock_detector.get_cluster.return_value = [101, 102]
        mock_detector.score_account.return_value = 0.45
        
        # Mock PyG data for cluster unscaling
        mock_pyg = MagicMock()
        mock_pyg.x = MagicMock()
        
        # Mock __getitem__ on pyg_data.x to return a mock tensor
        mock_tensor = MagicMock()
        mock_tensor.cpu.return_value.numpy.return_value.reshape.return_value = np.zeros((1, 74))
        mock_pyg.x.__getitem__.return_value = mock_tensor
        mock_detector.pyg_data = mock_pyg
        
        # Mock scaler in detector
        mock_scaler = MagicMock()
        mock_scaler.inverse_transform.return_value = np.zeros((1, 74))
        mock_detector.scaler = mock_scaler
        
        mock_engine.detector = mock_detector
        mock_engine_cls.return_value = mock_engine
        
        # Mock feature store
        mock_store = MagicMock()
        mock_store.get.side_effect = lambda acc_id: np.zeros(300) if acc_id == 100 else None
        mock_store.health_check.return_value = True
        mock_store_cls.return_value = mock_store
        
        # Mock action engine
        mock_action = MagicMock()
        mock_action_cls.return_value = mock_action
        
        from phase3.api.main import app
        with TestClient(app) as client:
            yield client, mock_engine, mock_store, mock_action

def test_api_health(mock_app_state):
    client, _, _, _ = mock_app_state
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["feature_store"] == "ok"
    assert data["models"] == "loaded"

def test_api_score_success(mock_app_state):
    client, _, _, _ = mock_app_state
    req_body = {
        "account_id": 100,
        "transaction_amount": 50000.0,
        "channel": "UPI",
        "is_new_counterparty": True,
        "is_round_amount": False,
        "hour_of_day": 14
    }
    response = client.post("/api/v1/score", json=req_body)
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == 100
    assert data["composite_score"] == 45.2
    assert data["risk_tier"] == "MEDIUM"
    assert data["automated_action"] == "MONITOR"

def test_api_score_not_found(mock_app_state):
    client, _, _, _ = mock_app_state
    req_body = {
        "account_id": 999,  # Not found
        "transaction_amount": 100.0,
        "channel": "NEFT",
        "hour_of_day": 10
    }
    response = client.post("/api/v1/score", json=req_body)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_api_score_batch(mock_app_state):
    client, _, _, _ = mock_app_state
    req_body = {
        "requests": [
            {
                "account_id": 100,
                "transaction_amount": 1000.0,
                "channel": "UPI",
                "hour_of_day": 12
            },
            {
                "account_id": 999,  # should be skipped
                "transaction_amount": 200.0,
                "channel": "RTGS",
                "hour_of_day": 15
            }
        ]
    }
    response = client.post("/api/v1/score/batch", json=req_body)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["account_id"] == 100

def test_api_cluster_success(mock_app_state):
    client, _, _, _ = mock_app_state
    req_body = {
        "account_id": 100,
        "hop_depth": 2
    }
    response = client.post("/api/v1/cluster", json=req_body)
    assert response.status_code == 200
    data = response.json()
    assert data["root_account_id"] == 100
    assert len(data["cluster_nodes"]) == 2
    assert data["cluster_nodes"][0]["account_id"] in [101, 102]
    assert data["relay_chain_detected"] is False
