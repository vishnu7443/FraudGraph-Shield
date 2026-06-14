import sqlite3
import os
import time
import structlog
from typing import List, Optional
from models.crypto_alert import CryptoAlert

logger = structlog.get_logger()

class CryptoAlertsDB:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.abspath(os.path.join(current_dir, "../storage"))
            os.makedirs(storage_dir, exist_ok=True)
            db_path = os.path.join(storage_dir, "crypto_alerts.db")
            
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
                    CREATE TABLE IF NOT EXISTS crypto_alerts (
                        alert_id TEXT PRIMARY KEY,
                        txn_id TEXT NOT NULL,
                        account_id INTEGER NOT NULL,
                        exchange TEXT NOT NULL,
                        amount REAL NOT NULL,
                        risk_score REAL NOT NULL,
                        severity TEXT NOT NULL,
                        hold_reason TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        status TEXT NOT NULL
                    )
                """)
                conn.commit()
            logger.info("crypto_alerts_db_initialized", path=self.db_path)
        except Exception as e:
            logger.error("crypto_alerts_db_init_failed", error=str(e))

    def save_alert(self, alert: CryptoAlert) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO crypto_alerts (
                        alert_id, txn_id, account_id, exchange, amount, 
                        risk_score, severity, hold_reason, timestamp, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        alert.alert_id, alert.txn_id, alert.account_id, alert.exchange,
                        alert.amount, alert.risk_score, alert.severity, alert.hold_reason,
                        alert.timestamp, alert.status
                    )
                )
                conn.commit()
            logger.info("crypto_alert_saved", alert_id=alert.alert_id)
            return True
        except Exception as e:
            logger.error("crypto_alert_save_failed", alert_id=alert.alert_id, error=str(e))
            return False

    def get_all_alerts(self) -> List[CryptoAlert]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM crypto_alerts ORDER BY timestamp DESC")
                rows = cursor.fetchall()
                alerts = []
                for row in rows:
                    alerts.append(CryptoAlert(
                        alert_id=row["alert_id"],
                        txn_id=row["txn_id"],
                        account_id=row["account_id"],
                        exchange=row["exchange"],
                        amount=row["amount"],
                        risk_score=row["risk_score"],
                        severity=row["severity"],
                        hold_reason=row["hold_reason"],
                        timestamp=row["timestamp"],
                        status=row["status"]
                    ))
                return alerts
        except Exception as e:
            logger.error("get_all_alerts_failed", error=str(e))
            return []

    def get_alert_by_id(self, alert_id: str) -> Optional[CryptoAlert]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM crypto_alerts WHERE alert_id = ?", (alert_id,))
                row = cursor.fetchone()
                if row:
                    return CryptoAlert(
                        alert_id=row["alert_id"],
                        txn_id=row["txn_id"],
                        account_id=row["account_id"],
                        exchange=row["exchange"],
                        amount=row["amount"],
                        risk_score=row["risk_score"],
                        severity=row["severity"],
                        hold_reason=row["hold_reason"],
                        timestamp=row["timestamp"],
                        status=row["status"]
                    )
                return None
        except Exception as e:
            logger.error("get_alert_by_id_failed", alert_id=alert_id, error=str(e))
            return None

# Global instance for app usage
db_instance = CryptoAlertsDB()
