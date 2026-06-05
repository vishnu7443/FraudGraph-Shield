# phase3/tests/test_latency.py
#
# P99 latency benchmark — verifies that 50 sequential scoring requests
# all complete within the 350 ms budget (with mocked models).

import pytest
import time
import numpy as np
from unittest.mock import MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="module")
def patched_app():
    """Return a FastAPI app with mocked dependencies via create_app()."""
    mock_engine = MagicMock()
    mock_engine.score_transaction = AsyncMock(return_value={
        "account_id": 0,
        "composite_score": 35.0,
        "risk_tier": "LOW",
        "automated_action": "ALLOW",
        "lgbm_score": 0.30,
        "gnn_mule_score": 0.25,
        "cfms_alert_active": False,
        "cfms_alert_age_hours": None,
        "top_shap_factors": [],
        "inference_latency_ms": 18.0,
        "model_version": "v1.0.0"
    })

    mock_store = MagicMock()
    mock_store.get.return_value = np.zeros(300, dtype=np.float32)
    mock_store.health_check.return_value = True

    mock_action = MagicMock()

    from phase3.api.main import create_app
    app = create_app(
        engine=mock_engine,
        feature_store=mock_store,
        action_engine=mock_action,
    )
    return app


@pytest.mark.asyncio
async def test_p99_latency_under_350ms(patched_app):
    async with AsyncClient(
        transport=ASGITransport(app=patched_app), base_url="http://test"
    ) as client:
        latencies = []
        payload = {
            "account_id": 0,
            "transaction_amount": 25000.0,
            "channel": "UPI",
            "hour_of_day": 14
        }
        for _ in range(50):
            start = time.perf_counter()
            resp = await client.post("/api/v1/score", json=payload)
            latencies.append((time.perf_counter() - start) * 1000)
            assert resp.status_code == 200

        latencies.sort()
        p99 = latencies[int(0.99 * len(latencies))]
        p50 = latencies[int(0.50 * len(latencies))]
        print(f"\nP50 latency: {p50:.1f}ms | P99 latency: {p99:.1f}ms")
        assert p99 < 350, f"P99 latency {p99:.1f}ms exceeds 350ms target"
