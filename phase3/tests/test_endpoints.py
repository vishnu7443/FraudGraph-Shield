# phase3/tests/test_endpoints.py
#
# Async integration tests using httpx AsyncClient with injected mock dependencies.

# pyrefly: ignore [missing-import]
import pytest
import pytest_asyncio
import numpy as np
from unittest.mock import MagicMock, AsyncMock
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="module")
def patched_app():
    """Return a FastAPI app with mocked dependencies via create_app()."""
    # --- fusion engine mock ---
    mock_engine = MagicMock()
    mock_engine.score_transaction = AsyncMock(return_value={
        "account_id": 0,
        "composite_score": 62.5,
        "risk_tier": "MEDIUM",
        "automated_action": "MONITOR",
        "lgbm_score": 0.55,
        "gnn_mule_score": 0.60,
        "cfms_alert_active": False,
        "cfms_alert_age_hours": None,
        "top_shap_factors": [
            {"feature_name": "F1", "contribution": 0.12, "direction": "increases_risk"}
        ],
        "inference_latency_ms": 23.4,
        "model_version": "v1.0.0"
    })

    # detector for /cluster
    mock_det = MagicMock()
    mock_det.get_cluster.return_value = [1, 2, 3]
    mock_det.score_account.return_value = 0.42
    mock_pyg = MagicMock()
    t = MagicMock()
    t.cpu.return_value.numpy.return_value.reshape.return_value = np.zeros((1, 74))
    mock_pyg.x.__getitem__ = MagicMock(return_value=t)
    mock_det.pyg_data = mock_pyg
    mock_scaler = MagicMock()
    mock_scaler.inverse_transform.return_value = np.zeros((1, 74))
    mock_det.scaler = mock_scaler
    mock_engine.detector = mock_det

    # --- feature store mock ---
    mock_store = MagicMock()
    mock_store.get.return_value = np.zeros(300, dtype=np.float32)
    mock_store.health_check.return_value = True

    # --- action engine mock ---
    mock_action = MagicMock()

    from phase3.api.main import create_app
    app = create_app(
        engine=mock_engine,
        feature_store=mock_store,
        action_engine=mock_action,
    )
    return app


@pytest_asyncio.fixture
async def client(patched_app):
    async with AsyncClient(
        transport=ASGITransport(app=patched_app), base_url="http://test"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["models"] == "loaded"


@pytest.mark.asyncio
async def test_score_endpoint_returns_valid_schema(client):
    payload = {
        "account_id": 0,
        "transaction_amount": 50000.0,
        "channel": "UPI",
        "is_new_counterparty": True,
        "is_round_amount": True,
        "hour_of_day": 2
    }
    resp = await client.post("/api/v1/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "composite_score" in data
    assert "automated_action" in data
    assert "top_shap_factors" in data
    assert 0 <= data["composite_score"] <= 100
    assert data["automated_action"] in ["ALLOW", "MONITOR", "HOLD", "BLOCK"]


@pytest.mark.asyncio
async def test_score_returns_latency_header(client):
    payload = {
        "account_id": 1,
        "transaction_amount": 10000.0,
        "channel": "NEFT",
        "hour_of_day": 10
    }
    resp = await client.post("/api/v1/score", json=payload)
    assert "X-Latency-Ms" in resp.headers
    assert float(resp.headers["X-Latency-Ms"]) < 350


@pytest.mark.asyncio
async def test_invalid_amount_rejected(client):
    payload = {
        "account_id": 0,
        "transaction_amount": -100.0,
        "channel": "UPI",
        "hour_of_day": 10
    }
    resp = await client.post("/api/v1/score", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_scoring_returns_list(client):
    payload = {"requests": [
        {"account_id": 0, "transaction_amount": 5000, "channel": "UPI", "hour_of_day": 9},
        {"account_id": 1, "transaction_amount": 75000, "channel": "NEFT", "hour_of_day": 3},
    ]}
    resp = await client.post("/api/v1/score/batch", json=payload)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 2
