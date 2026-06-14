import json
import os
import structlog
from typing import Optional

logger = structlog.get_logger()

class TravelRuleLogger:
    def __init__(self, logs_dir: Optional[str] = None):
        if not logs_dir:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            logs_dir = os.path.abspath(os.path.join(current_dir, "../travel_rule_logs"))
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)

    def log_travel_rule(self, txn_id: str, account_id: int, exchange: str, amount: float) -> str:
        payload = {
            "originator": f"MASKED-ACC-{account_id}",
            "originating_institution": "Bank of India",
            "beneficiary_exchange": exchange,
            "transaction_id": txn_id,
            "amount_inr": amount,
            "country": "India",
            "compliance_status": "PENDING_HOLD"
        }
        
        file_path = os.path.join(self.logs_dir, f"TravelRule_{txn_id}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.info("travel_rule_logged", file_path=file_path)
            return file_path
        except Exception as e:
            logger.error("travel_rule_logging_failed", txn_id=txn_id, error=str(e))
            return ""

travel_rule_logger = TravelRuleLogger()
