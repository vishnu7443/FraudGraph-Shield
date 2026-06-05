from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum

class AccountType(str, Enum):
    SAVINGS = "Savings"
    CURRENT = "Current"
    MSME_MICRO = "MSME Micro"
    MSME_MEDIUM = "MSME Medium"

class Channel(str, Enum):
    UPI = "UPI"
    NEFT = "NEFT"
    RTGS = "RTGS"
    ATM = "ATM"
    MOBILE = "MOBILE"

class TransactionScoreRequest(BaseModel):
    account_id: int = Field(..., description="Account node ID in graph")
    transaction_amount: float = Field(..., gt=0, description="Transaction amount in INR")
    channel: Channel
    is_new_counterparty: bool = False
    is_round_amount: bool = False
    hour_of_day: int = Field(..., ge=0, le=23)
    counterparty_account_id: Optional[int] = None

    @validator('transaction_amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Transaction amount must be positive')
        return round(v, 2)

class BatchScoreRequest(BaseModel):
    requests: List[TransactionScoreRequest] = Field(..., max_items=100)

class ClusterRequest(BaseModel):
    account_id: int
    hop_depth: int = Field(default=2, ge=1, le=3)
