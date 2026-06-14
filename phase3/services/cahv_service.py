import time
import random
import structlog
from typing import Optional, List, Dict
from vault.db import vault_db
from vault.encryption import encrypt, decrypt
from vault.hash_utils import hash_account_id

logger = structlog.get_logger()

class CAHVService:
    def create_profile(self, account_id: int, name: str, phone: str, pan: str, email: str) -> bool:
        """
        Encrypts PII fields and saves the customer profile to the secure SQLite vault database.
        """
        try:
            hashed_id = hash_account_id(account_id)
            enc_name = encrypt(name)
            enc_phone = encrypt(phone)
            enc_pan = encrypt(pan)
            enc_email = encrypt(email)
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
            res = vault_db.save_profile(
                account_id=account_id,
                hashed_id=hashed_id,
                enc_name=enc_name,
                enc_phone=enc_phone,
                enc_pan=enc_pan,
                enc_email=enc_email,
                created_at=timestamp
            )
            logger.info("cahv_profile_created", account_id=account_id, hashed_id=hashed_id)
            return res
        except Exception as e:
            logger.error("cahv_profile_creation_failed", account_id=account_id, error=str(e))
            return False

    def get_profile(self, hashed_id: str) -> Optional[Dict]:
        """
        Retrieves the profile from database and decrypts sensitive identity fields.
        """
        try:
            raw = vault_db.get_profile(hashed_id)
            if not raw:
                return None
            
            decrypted = {
                "account_id": raw["id"],
                "hashed_id": raw["hashed_id"],
                "name": decrypt(raw["encrypted_name"]),
                "phone": decrypt(raw["encrypted_phone"]),
                "pan": decrypt(raw["encrypted_pan"]),
                "email": decrypt(raw["encrypted_email"]),
                "created_at": raw["created_at"]
            }
            return decrypted
        except Exception as e:
            logger.error("cahv_profile_retrieval_failed", hashed_id=hashed_id, error=str(e))
            return None

    def create_alert(self, hashed_id: str, risk_score: float, alert_type: str, category: str, source: str, notes: str) -> str:
        """
        Registers a fraud event/alert for a given account hash.
        """
        try:
            alert_id = f"VALT-{int(time.time())}-{random.randint(1000, 9999)}-{hashed_id[:8]}"
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            res = vault_db.save_alert(
                alert_id=alert_id,
                hashed_id=hashed_id,
                risk_score=risk_score,
                alert_type=alert_type,
                category=category,
                source=source,
                notes=notes,
                created_at=timestamp
            )
            if res:
                logger.info("cahv_alert_created", alert_id=alert_id, hashed_id=hashed_id)
                return alert_id
            return ""
        except Exception as e:
            logger.error("cahv_alert_creation_failed", hashed_id=hashed_id, error=str(e))
            return ""

    def get_alerts(self, hashed_id: str) -> List[Dict]:
        """
        Fetches alert log history for an account hash.
        """
        try:
            return vault_db.get_alerts(hashed_id)
        except Exception as e:
            logger.error("cahv_alerts_retrieval_failed", hashed_id=hashed_id, error=str(e))
            return []

# Global CAHVService instance
cahv_service = CAHVService()
