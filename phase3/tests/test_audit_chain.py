# phase3/tests/test_audit_chain.py

import pytest
import pytest_asyncio
import tempfile
import os
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport

from vault.db import VaultDB
from core.audit_chain import calculate_log_hash, verify_chain_integrity, GENESIS_PREVIOUS_HASH

def test_hash_calculation():
    """Verify SHA-256 hash generation is deterministic and correct."""
    h = calculate_log_hash(
        index=1,
        timestamp="2026-06-16 10:00:00",
        action="INVESTIGATOR LOOKUP",
        username="analyst",
        role="analyst",
        endpoint="/vault/account",
        hashed_id="abc123xyz",
        previous_hash=GENESIS_PREVIOUS_HASH
    )
    # Check length (SHA-256 is 64 hex characters)
    assert len(h) == 64
    assert h == calculate_log_hash(
        1, "2026-06-16 10:00:00", "INVESTIGATOR LOOKUP", "analyst", "analyst", "/vault/account", "abc123xyz", GENESIS_PREVIOUS_HASH
    )
    # Any change modifies the hash
    assert h != calculate_log_hash(
        1, "2026-06-16 10:00:01", "INVESTIGATOR LOOKUP", "analyst", "analyst", "/vault/account", "abc123xyz", GENESIS_PREVIOUS_HASH
    )


def test_chain_incremental_building_and_tamper_detection():
    """Verify appending sequentially builds a chain and validation catches modifications."""
    fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        # 1. Initialize isolated test database
        db = VaultDB(temp_db_path)
        
        # Override the global vault_db temporarily inside vault.db
        # so that it tests against our temp database rather than the real one
        import vault.db
        original_db = vault.db.vault_db
        vault.db.vault_db = db
        
        try:
            # 2. Append records
            assert db.append_audit_log("2026-06-16 10:00:00", "LOOKUP", "analyst", "analyst", "/a", "hash1") is True
            assert db.append_audit_log("2026-06-16 10:05:00", "LOOKUP", "admin", "admin", "/b", "hash2") is True
            assert db.append_audit_log("2026-06-16 10:10:00", "ALERT", "analyst", "analyst", "/c", "hash3") is True
            
            # 3. Verify clean chain
            res = verify_chain_integrity()
            assert res["verified"] is True
            assert res["total_records"] == 3
            
            # 4. Simulate tampering (modify username of block #2)
            assert db.tamper_audit_log_record(2, "malicious_user") is True
            
            # 5. Verify tampered chain (should fail at index 2 due to content hash mismatch)
            res_tampered = verify_chain_integrity()
            assert res_tampered["verified"] is False
            assert res_tampered["tampered_index"] == 2
            assert "fields modified" in res_tampered["reason"]
            
        finally:
            vault.db.vault_db = original_db
            
    finally:
        import gc
        gc.collect()
        try:
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
        except PermissionError:
            pass


@pytest.fixture(scope="module")
def patched_app():
    """Generate FastAPI app with mocked engine and store to run API audit tests."""
    mock_engine = MagicMock()
    mock_store = MagicMock()
    mock_action = MagicMock()

    from phase3.api.main import create_app
    app = create_app(
        engine=mock_engine,
        feature_store=mock_store,
        action_engine=mock_action
    )
    return app


@pytest_asyncio.fixture
async def client(patched_app):
    async with AsyncClient(
        transport=ASGITransport(app=patched_app), base_url="http://test"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_audit_endpoints_require_authentication(client):
    """Verify audit endpoints reject unauthenticated queries with 401."""
    for path in ["/api/v1/audit/logs", "/api/v1/audit/verify"]:
        resp = await client.get(path)
        assert resp.status_code == 401
        
    resp = await client.post("/api/v1/audit/simulate-tamper", json={"log_index": 1})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_audit_endpoints_workloads_and_rbac(client):
    """Verify endpoint flows: login, verify integrity, log access logs, and Admin checks."""
    # 1. Obtain tokens
    analyst_resp = await client.post("/api/v1/auth/login", json={"username": "analyst", "password": "analyst_shield_2026"})
    analyst_token = analyst_resp.json()["access_token"]
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    
    admin_resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin_shield_2026"})
    admin_token = admin_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 2. Get Audit logs (Admin only!)
    resp = await client.get("/api/v1/audit/logs", headers=analyst_headers)
    assert resp.status_code == 403 # Analyst rejected
    
    resp = await client.get("/api/v1/audit/logs", headers=admin_headers)
    assert resp.status_code == 200 # Admin allowed
    assert isinstance(resp.json(), list)
    
    # 3. Verify Chain Integrity (Both Analyst and Admin)
    resp = await client.get("/api/v1/audit/verify", headers=analyst_headers)
    assert resp.status_code == 200
    assert "verified" in resp.json()
    
    resp = await client.get("/api/v1/audit/verify", headers=admin_headers)
    assert resp.status_code == 200
    assert "verified" in resp.json()
