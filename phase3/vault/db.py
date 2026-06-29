import sqlite3
import os
import structlog
from datetime import datetime, timezone, timedelta
from typing import List, Optional

logger = structlog.get_logger()

class VaultDB:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            if os.getenv("VERCEL"):
                db_path = "/tmp/cahv.db"
            else:
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
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        hashed_password TEXT NOT NULL,
                        full_name TEXT,
                        role TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1,
                        failed_attempts INTEGER DEFAULT 0,
                        locked_until TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        log_index INTEGER PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        action TEXT NOT NULL,
                        username TEXT NOT NULL,
                        role TEXT NOT NULL,
                        endpoint TEXT NOT NULL,
                        hashed_id TEXT,
                        previous_hash TEXT NOT NULL,
                        current_hash TEXT NOT NULL
                    )
                """)
                conn.commit()
            
            logger.info("cahv_vault_db_initialized", path=self.db_path)
            self._seed_default_users()
        except Exception as e:
            logger.error("cahv_vault_db_init_failed", error=str(e))

    def _seed_default_users(self):
        # Local import to avoid circular dependency issues
        from vault.security import hash_password
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) as count FROM users")
                row = cursor.fetchone()
                if row and row["count"] == 0:
                    logger.info("seeding_default_users")
                    now_str = datetime.now(timezone.utc).isoformat()
                    
                    # Create admin
                    admin_hash = hash_password("admin_shield_2026")
                    conn.execute(
                        "INSERT INTO users (username, hashed_password, full_name, role, created_at) VALUES (?, ?, ?, ?, ?)",
                        ("admin", admin_hash, "System Administrator", "admin", now_str)
                    )
                    
                    # Create analyst
                    analyst_hash = hash_password("analyst_shield_2026")
                    conn.execute(
                        "INSERT INTO users (username, hashed_password, full_name, role, created_at) VALUES (?, ?, ?, ?, ?)",
                        ("analyst", analyst_hash, "Lead Fraud Analyst", "analyst", now_str)
                    )
                    conn.commit()
                    logger.info("default_users_seeded_successfully")
        except Exception as e:
            logger.error("failed_to_seed_default_users", error=str(e))

    def get_user(self, username: str) -> Optional[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error("get_user_failed", username=username, error=str(e))
            return None

    def create_user(self, username: str, hashed_password: str, full_name: str, role: str) -> bool:
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO users (username, hashed_password, full_name, role, created_at) VALUES (?, ?, ?, ?, ?)",
                    (username.lower().strip(), hashed_password, full_name, role, now_str)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error("create_user_failed", username=username, error=str(e))
            return False

    def increment_failed_attempts(self, username: str) -> int:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT failed_attempts FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if not row:
                    return 0
                new_attempts = row["failed_attempts"] + 1
                conn.execute("UPDATE users SET failed_attempts = ? WHERE username = ?", (new_attempts, username))
                conn.commit()
            return new_attempts
        except Exception as e:
            logger.error("increment_failed_attempts_failed", username=username, error=str(e))
            return 0

    def reset_failed_attempts(self, username: str):
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?",
                    (username,)
                )
                conn.commit()
        except Exception as e:
            logger.error("reset_failed_attempts_failed", username=username, error=str(e))

    def lock_user(self, username: str, lock_minutes: int = 15):
        try:
            unlock_time = (datetime.now(timezone.utc) + timedelta(minutes=lock_minutes)).isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE users SET locked_until = ? WHERE username = ?",
                    (unlock_time, username)
                )
                conn.commit()
            logger.info("user_account_locked", username=username, until=unlock_time)
        except Exception as e:
            logger.error("lock_user_failed", username=username, error=str(e))

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

    def append_audit_log(self, timestamp: str, action: str, username: str, role: str, endpoint: str, hashed_id: Optional[str]) -> bool:
        try:
            with self._get_connection() as conn:
                # Get the last log to determine index and previous hash
                cursor = conn.execute("SELECT log_index, current_hash FROM audit_logs ORDER BY log_index DESC LIMIT 1")
                last_row = cursor.fetchone()
                if last_row:
                    next_index = last_row["log_index"] + 1
                    prev_hash = last_row["current_hash"]
                else:
                    next_index = 1
                    prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
                
                # Dynamic hash calculation
                from core.audit_chain import calculate_log_hash
                curr_hash = calculate_log_hash(
                    index=next_index,
                    timestamp=timestamp,
                    action=action,
                    username=username,
                    role=role,
                    endpoint=endpoint,
                    hashed_id=hashed_id,
                    previous_hash=prev_hash
                )
                
                conn.execute(
                    """
                    INSERT INTO audit_logs (
                        log_index, timestamp, action, username, role, endpoint, hashed_id, previous_hash, current_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (next_index, timestamp, action, username, role, endpoint, hashed_id, prev_hash, curr_hash)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error("append_audit_log_failed", username=username, error=str(e))
            return False

    def get_all_audit_logs(self) -> List[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM audit_logs ORDER BY log_index ASC")
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_all_audit_logs_failed", error=str(e))
            return []

    def tamper_audit_log_record(self, log_index: int, new_user: str) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE audit_logs SET username = ? WHERE log_index = ?",
                    (new_user, log_index)
                )
                conn.commit()
            logger.warning("audit_log_tampered_intentionally", index=log_index, new_user=new_user)
            return True
        except Exception as e:
            logger.error("tamper_audit_log_record_failed", index=log_index, error=str(e))
            return False

# Global Vault DB instance
vault_db = VaultDB()
