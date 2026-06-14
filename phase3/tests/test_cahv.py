# phase3/tests/test_cahv.py
#
# Automated test cases for the Cloud Account Holder Vault (CAHV) subsystem.
# Covers AES-256-GCM encryption, SHA-256 hashing, database profiles & alerts operations,
# and FastAPI endpoints integration tests.

import pytest
import pytest_asyncio
import sqlite3
import os
import hashlib
import time
from httpx import AsyncClient, ASGITransport

from vault.encryption import encrypt, decrypt
from vault.hash_utils import hash_account_id
from vault.db import vault_db
from services.cahv_service import cahv_service
from services.profile_enrichment import get_enriched_profile_summary
from api.main import create_app

# Fixture to set up a clean, isolated test database for CAHV
@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_db_path = os.path.join(current_dir, "../storage/test_cahv.db")
    
    # Override global vault_db path to avoid dirtying live/seed database
    original_path = vault_db.db_path
    vault_db.db_path = test_db_path
    vault_db._init_db()
    
    # Truncate tables for a clean start
    with vault_db._get_connection() as conn:
        conn.execute("DELETE FROM account_profiles")
        conn.execute("DELETE FROM fraud_alerts")
        conn.commit()
        
    yield
    
    # Restore original path and clean up test db file
    vault_db.db_path = original_path
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass

@pytest_asyncio.fixture
async def client():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# 1. Encryption Layer Tests
def test_encryption_roundtrip():
    secret_text = "John Doe Secret PAN 123456"
    ciphertext = encrypt(secret_text)
    assert ciphertext != secret_text
    assert len(ciphertext) > 56  # hex representation should be long enough
    
    decrypted = decrypt(ciphertext)
    assert decrypted == secret_text

def test_encryption_empty_strings():
    assert encrypt("") == ""
    assert decrypt("") == ""


# 2. Hashing Utilities Tests
def test_hash_consistency():
    acc_id = 987654321
    hash1 = hash_account_id(acc_id)
    hash2 = hash_account_id(acc_id)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 output length in hex

def test_hash_uniqueness():
    hash1 = hash_account_id(1111)
    hash2 = hash_account_id(2222)
    assert hash1 != hash2


# 3. Vault Service Layer Tests
def test_cahv_profile_creation_and_retrieval():
    acc_id = 5555
    hashed_id = hash_account_id(acc_id)
    
    success = cahv_service.create_profile(
        account_id=acc_id,
        name="Test Investigator",
        phone="+91 99999 88888",
        pan="TESTP1234A",
        email="test@investigator.in"
    )
    assert success is True
    
    profile = cahv_service.get_profile(hashed_id)
    assert profile is not None
    assert profile["account_id"] == acc_id
    assert profile["name"] == "Test Investigator"
    assert profile["phone"] == "+91 99999 88888"
    assert profile["pan"] == "TESTP1234A"
    assert profile["email"] == "test@investigator.in"

def test_cahv_alert_logging_and_enrichment():
    acc_id = 7777
    hashed_id = hash_account_id(acc_id)
    
    # Register profile first
    cahv_service.create_profile(acc_id, "Alert User", "+91 77777 77777", "ALERTP1234B", "alert@user.com")
    
    # Create multiple alerts
    alert1 = cahv_service.create_alert(
        hashed_id=hashed_id,
        risk_score=45.5,
        alert_type="SUSPICIOUS_VELOCITY",
        category="Transaction Risk",
        source="Fusion Engine",
        notes="Testing alert 1"
    )
    assert alert1.startswith("VALT-")
    
    # Sleep to ensure different timestamps for descending sorting order
    time.sleep(1.1)
    
    alert2 = cahv_service.create_alert(
        hashed_id=hashed_id,
        risk_score=88.2,
        alert_type="CRYPTO_EXIT",
        category="Crypto Risk",
        source="Crypto Detector",
        notes="Testing alert 2"
    )
    assert alert2.startswith("VALT-")
    
    alerts = cahv_service.get_alerts(hashed_id)
    assert len(alerts) == 2
    assert alerts[0]["alert_id"] == alert2  # descending by created_at time
    assert alerts[0]["risk_score"] == 88.2
    assert alerts[0]["category"] == "Crypto Risk"
    assert alerts[0]["source"] == "Crypto Detector"
    
    # Profile Enrichment checks
    summary = get_enriched_profile_summary(hashed_id)
    assert summary["total_alerts"] == 2
    assert summary["highest_risk"] == 88.2
    assert summary["last_alert"] != "NEVER"


# 4. API Endpoints Tests
@pytest.mark.asyncio
async def test_api_create_profile(client):
    payload = {
        "account_id": 8888,
        "name": "FastAPI Tester",
        "phone": "+91 88888 88888",
        "pan": "FASTP1234C",
        "email": "fastapi@tester.in"
    }
    resp = await client.post("/api/v1/vault/account", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "hashed_id" in data

@pytest.mark.asyncio
async def test_api_create_alert_and_get_summary(client):
    acc_id = 8888
    hashed_id = hash_account_id(acc_id)
    
    # Log an alert via API
    alert_payload = {
        "hashed_id": hashed_id,
        "risk_score": 95.5,
        "alert_type": "MULE_CONFIRMED",
        "category": "Identity Risk",
        "source": "Manual Investigator",
        "notes": "FastAPI alert test"
    }
    resp_alert = await client.post("/api/v1/vault/alert", json=alert_payload)
    assert resp_alert.status_code == 200
    assert resp_alert.json()["success"] is True
    
    # Get unified case profile response
    resp_profile = await client.get(f"/api/v1/vault/account/{hashed_id}")
    assert resp_profile.status_code == 200
    data = resp_profile.json()
    
    assert "profile" in data
    assert "summary" in data
    assert "alerts" in data
    
    assert data["profile"]["name"] == "FastAPI Tester"
    assert data["summary"]["total_alerts"] == 1
    assert data["summary"]["highest_risk"] == 95.5
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["category"] == "Identity Risk"
    assert data["alerts"][0]["source"] == "Manual Investigator"
