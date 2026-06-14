from pydantic import BaseModel
from typing import Optional

class CryptoAlert(BaseModel):
    alert_id: str
    txn_id: str
    account_id: int
    exchange: str
    amount: float
    risk_score: float
    severity: str
    hold_reason: str
    timestamp: str  # ISO 8601 string format
    status: str     # "OPEN", "RESOLVED"
