# phase3/vault/security.py

import os
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import structlog

logger = structlog.get_logger()

# Config keys
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_jwt_secret_key_fraudgraph_shield_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
PBKDF2_ITERATIONS = 100000

def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256.
    Returns format: pbkdf2:sha256:100000$salt$hash
    """
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt}${pw_hash}"

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a password against the stored PBKDF2 hash.
    """
    if not hashed_password or "$" not in hashed_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        
        algo_part, salt, pw_hash = parts
        # Parse iterations and algorithm
        meta = algo_part.split(":")
        if len(meta) != 3 or meta[0] != "pbkdf2" or meta[1] != "sha256":
            return False
            
        iterations = int(meta[2])
        
        calculated_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        ).hex()
        
        return secrets.compare_digest(calculated_hash, pw_hash)
    except Exception as e:
        logger.error("password_verification_error", error=str(e))
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a new access JWT signed with HS256.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Cast to integer timestamp for standard JWT 'exp' claim
    to_encode.update({
        "exp": int(expire.timestamp()),
        "type": "access"
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a new refresh JWT signed with HS256.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
    to_encode.update({
        "exp": int(expire.timestamp()),
        "type": "refresh"
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """
    Decodes a JWT and verifies signature, expiration, and algorithm.
    Raises jwt.PyJWTError on validation failure.
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
