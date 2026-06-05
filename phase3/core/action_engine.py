# phase3/core/action_engine.py

import structlog
import time
from typing import Optional

logger = structlog.get_logger()

class ActionEngine:

    def execute(self, account_id: int, action: str, score: float,
                composite_result: dict) -> dict:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if action == "ALLOW":
            return self._allow(account_id, score, timestamp)
        elif action == "MONITOR":
            return self._monitor(account_id, score, timestamp)
        elif action == "HOLD":
            return self._hold(account_id, score, timestamp)
        elif action == "BLOCK":
            return self._block(account_id, score, timestamp, composite_result)

    def _allow(self, account_id, score, ts):
        logger.info("action_allow", account_id=account_id, score=score)
        return {"action": "ALLOW", "timestamp": ts, "message": "Transaction cleared."}

    def _monitor(self, account_id, score, ts):
        logger.warning("action_monitor", account_id=account_id, score=score)
        return {
            "action": "MONITOR",
            "timestamp": ts,
            "message": "Transaction cleared. Account flagged for enhanced monitoring.",
            "review_deadline_hours": 4
        }

    def _hold(self, account_id, score, ts):
        logger.warning("action_hold", account_id=account_id, score=score)
        return {
            "action": "HOLD",
            "timestamp": ts,
            "message": "Transaction held for 15 minutes pending analyst review.",
            "hold_duration_minutes": 15,
            "tms_alert_generated": True
        }

    def _block(self, account_id, score, ts, result):
        logger.error("action_block", account_id=account_id, score=score)
        # In production: trigger CBS account freeze + FIU-IND STR
        str_reference = f"STR-{account_id}-{int(time.time())}"
        cfms_ticket = f"CFMS-AUTO-{account_id}-{int(time.time())}"
        return {
            "action": "BLOCK",
            "timestamp": ts,
            "message": "Transaction blocked. Account frozen pending investigation.",
            "str_reference": str_reference,
            "cfms_ticket_created": cfms_ticket,
            "fiu_ind_filing_initiated": True,
            "analyst_queue_priority": "URGENT"
        }
