# phase3/tests/test_auth.py

import pytest
import pytest_asyncio
import tempfile
import os
import time
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock

from vault.db import VaultDB
from vault.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)

def test_password_security():
    """Verify PBKDF2 hashing works correctly and safely verifies password inputs."""
    pw = "super_secret_analyst_2026"
    hashed = hash_password(pw)
    assert hashed.startswith("pbkdf2:sha256:100000$")
    
    # Test valid and invalid attempts
    assert verify_password(pw, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(pw, "invalid_hash_string") is False


def test_database_operations_and_lockout():
    """Verify user registration, lockout increments, and unlock resets in database."""
    fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = VaultDB(temp_db_path)
        username = "johndoe"
        hashed = hash_password("password123")
        
        # Test creation
        assert db.create_user(username, hashed, "John Doe", "analyst") is True
        user = db.get_user(username)
        assert user is not None
        assert user["username"] == username
        assert user["full_name"] == "John Doe"
        assert user["role"] == "analyst"
        assert user["failed_attempts"] == 0
        assert user["locked_until"] is None
        
        # Test incrementing failed attempts
        assert db.increment_failed_attempts(username) == 1
        assert db.increment_failed_attempts(username) == 2
        user = db.get_user(username)
        assert user["failed_attempts"] == 2
        
        # Test lockout timestamp generation
        db.lock_user(username, lock_minutes=5)
        user = db.get_user(username)
        assert user["locked_until"] is not None
        
        # Test lockout reset
        db.reset_failed_attempts(username)
        user = db.get_user(username)
        assert user["failed_attempts"] == 0
        assert user["locked_until"] is None
        
    finally:
        import gc
        gc.collect()
        try:
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
        except PermissionError:
            pass


def test_jwt_generation_and_decoding():
    """Verify Access and Refresh tokens signature integrity and payloads."""
    payload = {"sub": "analyst_john", "role": "analyst"}
    
    access = create_access_token(payload)
    refresh = create_refresh_token(payload)
    
    # Check headers/decoding
    decoded_access = decode_token(access)
    assert decoded_access["sub"] == "analyst_john"
    assert decoded_access["role"] == "analyst"
    assert decoded_access["type"] == "access"
    assert "exp" in decoded_access
    
    decoded_refresh = decode_token(refresh)
    assert decoded_refresh["sub"] == "analyst_john"
    assert decoded_refresh["role"] == "analyst"
    assert decoded_refresh["type"] == "refresh"


@pytest.fixture(scope="module")
def patched_app():
    """Generate FastAPI app with mocked engine and store to run API auth tests."""
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
async def test_auth_secured_endpoints_deny_unauthenticated(client):
    """Secure vault and crypto alert endpoints should block unauthenticated users."""
    endpoints = [
        ("GET", "/api/v1/vault/account/some_hash"),
        ("GET", "/api/v1/vault/alerts/some_hash"),
        ("POST", "/api/v1/vault/account"),
        ("POST", "/api/v1/vault/alert"),
        ("GET", "/api/v1/crypto-alerts"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = await client.get(path)
        else:
            resp = await client.post(path, json={})
        assert resp.status_code == 401, f"Expected 401 for {method} {path}"
        assert resp.json()["detail"] == "Not authenticated" or "credentials" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_api_login_success_and_failures(client):
    """Test login execution, brute force increments, and lockout responses."""
    # Ensure default admin and analyst users exist in db
    from vault.db import vault_db
    
    # 1. Success login
    login_payload = {"username": "analyst", "password": "analyst_shield_2026"}
    resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "analyst"
    assert data["username"] == "analyst"
    
    # 2. Failure login
    bad_payload = {"username": "analyst", "password": "wrongpassword"}
    resp = await client.post("/api/v1/auth/login", json=bad_payload)
    assert resp.status_code == 401
    
    # 3. Trigger lockout (5 consecutive failed attempts)
    vault_db.reset_failed_attempts("analyst")
    for _ in range(5):
        resp = await client.post("/api/v1/auth/login", json=bad_payload)
    
    # Attempt 6 should return 403 Forbidden due to lockout
    resp = await client.post("/api/v1/auth/login", json=bad_payload)
    assert resp.status_code == 403
    assert "locked" in resp.json()["detail"]
    
    # Reset default state for other tests
    vault_db.reset_failed_attempts("analyst")


@pytest.mark.asyncio
async def test_auth_refresh_token(client):
    """Test generating a new access token using a refresh token."""
    login_payload = {"username": "analyst", "password": "analyst_shield_2026"}
    resp = await client.post("/api/v1/auth/login", json=login_payload)
    data = resp.json()
    refresh_token = data["refresh_token"]
    
    refresh_payload = {"refresh_token": refresh_token}
    resp = await client.post("/api/v1/auth/refresh", json=refresh_payload)
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_role_based_access_control(client):
    """Test that Analysts can view/create alerts, but only Admins can create profiles and new users."""
    # Obtain analyst token
    analyst_resp = await client.post("/api/v1/auth/login", json={"username": "analyst", "password": "analyst_shield_2026"})
    analyst_token = analyst_resp.json()["access_token"]
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    
    # Obtain admin token
    admin_resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin_shield_2026"})
    admin_token = admin_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Profile registration (Admin-only)
    profile_payload = {
        "account_id": 9999,
        "name": "Test User",
        "phone": "+91 00000 00000",
        "pan": "ABCDE1234F",
        "email": "test@domain.com"
    }
    
    # Analyst tries to create profile -> should return 403 Forbidden
    resp = await client.post("/api/v1/vault/account", json=profile_payload, headers=analyst_headers)
    assert resp.status_code == 403
    
    # Admin tries to create profile -> should return 200 or 500 (if service isn't fully mocked but authentication succeeds!)
    resp = await client.post("/api/v1/vault/account", json=profile_payload, headers=admin_headers)
    # Since mock service for profile creation in cahv_service is initialized to sqlite DB, this should return 200 Success!
    assert resp.status_code == 200
    
    # 2. User Creation endpoint /auth/create-user (Admin-only)
    new_user_payload = {
        "username": "temp_analyst",
        "password": "temp_password_2026",
        "full_name": "Temporary Analyst",
        "role": "analyst"
    }
    
    # Analyst tries to create user -> should return 403
    resp = await client.post("/api/v1/auth/create-user", json=new_user_payload, headers=analyst_headers)
    assert resp.status_code == 403
    
    # Admin tries to create user -> should return 201 Created
    # Clean up existing test user if any
    from vault.db import vault_db
    try:
        with vault_db._get_connection() as conn:
            conn.execute("DELETE FROM users WHERE username = 'temp_analyst'")
            conn.commit()
    except Exception:
        pass
        
    resp = await client.post("/api/v1/auth/create-user", json=new_user_payload, headers=admin_headers)
    assert resp.status_code == 201
