# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from phase3.core.cfms_mock import cfms_app, MOCK_ALERT_REGISTRY

client = TestClient(cfms_app)

def test_cfms_health():
    response = client.get("/cfms/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "registry_size" in data
    assert data["registry_size"] == len(MOCK_ALERT_REGISTRY)

def test_cfms_alert_active():
    if not MOCK_ALERT_REGISTRY:
        # Fallback if registry is empty (though highly unlikely)
        return
    active_account_id = next(iter(MOCK_ALERT_REGISTRY.keys()))
    response = client.get(f"/cfms/alert/{active_account_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == active_account_id
    assert data["alert_active"] is True
    assert data["ticket_id"] is not None
    assert data["fraud_type"] is not None
    assert data["alert_age_hours"] is not None
    assert data["severity"] is not None
    assert data["reporting_bank"] is not None

def test_cfms_alert_inactive():
    # Find an account that is not in the registry
    inactive_account_id = 99999
    assert inactive_account_id not in MOCK_ALERT_REGISTRY
    response = client.get(f"/cfms/alert/{inactive_account_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == inactive_account_id
    assert data["alert_active"] is False
    assert data["ticket_id"] is None
    assert data["fraud_type"] is None
    assert data["alert_age_hours"] is None
    assert data["severity"] is None
    assert data["reporting_bank"] is None
