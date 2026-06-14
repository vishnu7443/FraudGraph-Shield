import json
import os
import structlog
from typing import Optional

logger = structlog.get_logger()

class STRGenerator:
    def __init__(self, reports_dir: Optional[str] = None):
        if not reports_dir:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            reports_dir = os.path.abspath(os.path.join(current_dir, "../reports"))
        self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

    def generate_vda_str(self, txn_id: str, account_id: int, exchange: str, amount: float, score: float, hold_reason: str) -> str:
        report = {
            "report_type": "VDA-STR",
            "report_format_version": "1.0",
            "fiu_ind_prescribed": True,
            "transaction_details": {
                "txn_id": txn_id,
                "amount_inr": amount,
                "routing_type": "VDA_EXIT",
                "destination_exchange": exchange
            },
            "originator_details": {
                "account_id": account_id,
                "institution": "Bank of India"
            },
            "risk_analysis": {
                "composite_score": score,
                "flagged_reason": hold_reason,
                "explainability": "SHAP feature correlation combined with high-risk VDA exit detection logic"
            },
            "regulatory_action": {
                "action": "HOLD",
                "authority_notified": "FIU-IND"
            }
        }
        
        file_path = os.path.join(self.reports_dir, f"VDA_STR_{txn_id}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logger.info("vda_str_generated", file_path=file_path)
            return file_path
        except Exception as e:
            logger.error("vda_str_generation_failed", txn_id=txn_id, error=str(e))
            return ""

str_generator = STRGenerator()
