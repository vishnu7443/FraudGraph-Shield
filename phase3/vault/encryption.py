import os
import hashlib
import structlog
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = structlog.get_logger()

# Derive a 32-byte key from the environment variable (or a secure default) using SHA-256
raw_key = os.getenv("CAHV_ENCRYPTION_KEY", "default_secret_key_cahv_vault_2026")
KEY = hashlib.sha256(raw_key.encode('utf-8')).digest()

def encrypt(text: str) -> str:
    """
    Encrypts plaintext using AES-256-GCM.
    Returns hex representation of concat(tag [16 bytes], IV [12 bytes], ciphertext).
    """
    if not text:
        return ""
    try:
        iv = os.urandom(12)
        encryptor = Cipher(
            algorithms.AES(KEY),
            modes.GCM(iv),
            backend=default_backend()
        ).encryptor()
        ciphertext = encryptor.update(text.encode('utf-8')) + encryptor.finalize()
        return (encryptor.tag + iv + ciphertext).hex()
    except Exception as e:
        logger.error("encryption_failed", error=str(e))
        raise

def decrypt(hex_str: str) -> str:
    """
    Decrypts AES-256-GCM ciphertext hex.
    """
    if not hex_str:
        return ""
    try:
        data = bytes.fromhex(hex_str)
        if len(data) < 28:
            raise ValueError("Ciphertext data too short")
        tag = data[:16]
        iv = data[16:28]
        ciphertext = data[28:]
        decryptor = Cipher(
            algorithms.AES(KEY),
            modes.GCM(iv, tag),
            backend=default_backend()
        ).decryptor()
        return (decryptor.update(ciphertext) + decryptor.finalize()).decode('utf-8')
    except Exception as e:
        logger.error("decryption_failed", error=str(e))
        raise
