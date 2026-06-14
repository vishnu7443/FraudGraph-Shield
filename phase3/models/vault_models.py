from pydantic import BaseModel
from typing import Optional

class AccountProfile(BaseModel):
    hashed_id: str
    name: str
    phone: str
    email: str
    pan: str
    created_at: str

class VaultFraudAlert(BaseModel):
    alert_id: str
    hashed_id: str
    risk_score: float
    alert_type: str
    category: str
    source: str
    notes: str
    created_at: str
