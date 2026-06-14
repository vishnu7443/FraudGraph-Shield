import sqlite3
import os
import structlog
from typing import List, Optional

logger = structlog.get_logger()

class VaultDB:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.abspath(os.path.join(current_dir, "../storage"))
            os.makedirs(storage_dir, exist_ok=True)
            db_path = os.path.join(storage_dir, "cahv.db")
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS account_profiles (
                        id INTEGER PRIMARY KEY,
                        hashed_id TEXT UNIQUE,
                        encrypted_name TEXT,
                        encrypted_phone TEXT,
                        encrypted_pan TEXT,
                        encrypted_email TEXT,
                        created_at TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS fraud_alerts (
                        alert_id TEXT PRIMARY KEY,
                        hashed_id TEXT,
                        risk_score REAL,
                        alert_type TEXT,
                        category TEXT,
                        source TEXT,
                        notes TEXT,
                        created_at TEXT
                    )
                """)
                conn.commit()
            logger.info("cahv_vault_db_initialized", path=self.db_path)
        except Exception as e:
            logger.error("cahv_vault_db_init_failed", error=str(e))

    def save_profile(self, account_id: int, hashed_id: str, enc_name: str, enc_phone: str, enc_pan: str, enc_email: str, created_at: str) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO account_profiles (
                        id, hashed_id, encrypted_name, encrypted_phone, encrypted_pan, encrypted_email, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(hashed_id) DO UPDATE SET
                        encrypted_name=excluded.encrypted_name,
                        encrypted_phone=excluded.encrypted_phone,
                        encrypted_pan=excluded.encrypted_pan,
                        encrypted_email=excluded.encrypted_email
                    """,
                    (account_id, hashed_id, enc_name, enc_phone, enc_pan, enc_email, created_at)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error("save_profile_failed", hashed_id=hashed_id, error=str(e))
            return False

    def get_profile(self, hashed_id: str) -> Optional[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM account_profiles WHERE hashed_id = ?", (hashed_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error("get_profile_failed", hashed_id=hashed_id, error=str(e))
            return None

    def save_alert(self, alert_id: str, hashed_id: str, risk_score: float, alert_type: str, category: str, source: str, notes: str, created_at: str) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO fraud_alerts (
                        alert_id, hashed_id, risk_score, alert_type, category, source, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (alert_id, hashed_id, risk_score, alert_type, category, source, notes, created_at)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error("save_alert_failed", alert_id=alert_id, error=str(e))
            return False

    def get_alerts(self, hashed_id: str) -> List[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM fraud_alerts WHERE hashed_id = ? ORDER BY created_at DESC", (hashed_id,))
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_alerts_failed", hashed_id=hashed_id, error=str(e))
            return []

# Global Vault DB instance
vault_db = VaultDB()
