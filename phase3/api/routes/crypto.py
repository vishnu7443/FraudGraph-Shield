from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import List
from models.crypto_alert import CryptoAlert
from storage.db import db_instance
import time

router = APIRouter()

@router.get("/crypto-alerts", response_model=List[CryptoAlert])
async def get_crypto_alerts():
    return db_instance.get_all_alerts()

@router.get("/crypto-alerts/{alert_id}", response_model=CryptoAlert)
async def get_crypto_alert(alert_id: str):
    alert = db_instance.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert

class ManualAlertRequest(BaseModel):
    txn_id: str = Field(..., description="Unique transaction reference ID")
    account_id: int = Field(..., description="Target bank account ID")
    exchange: str = Field(..., description="Identified cryptocurrency exchange")
    amount: float = Field(..., gt=0, description="Transaction exit amount in INR")
    risk_score: float = Field(..., ge=0, le=100, description="Risk fusion score (0-100)")

@router.post("/crypto-alerts/generate", response_model=CryptoAlert)
async def generate_manual_alert(request: Request, body: ManualAlertRequest):
    from core.config import settings
    
    # 1. Determine alert severity
    if body.risk_score >= settings.SEVERITY_THRESHOLD_CRITICAL:
        severity = "CRITICAL"
    elif body.risk_score >= settings.SEVERITY_THRESHOLD_HIGH:
        severity = "HIGH"
    elif body.risk_score >= settings.SEVERITY_THRESHOLD_MEDIUM:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    hold_reason = f"Funds exiting to high-risk VDA provider {body.exchange} (Manual trigger)"
    alert_id = f"ALT-{body.account_id}-{int(time.time())}"
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 2. Create alert structure
    alert = CryptoAlert(
        alert_id=alert_id,
        txn_id=body.txn_id,
        account_id=body.account_id,
        exchange=body.exchange,
        amount=body.amount,
        risk_score=body.risk_score,
        severity=severity,
        hold_reason=hold_reason,
        timestamp=timestamp,
        status="OPEN"
    )

    # 3. Save to database
    db_instance.save_alert(alert)
    
    # 4. Generate STR and Travel Rule logs
    from services.str_generator import str_generator
    from services.travel_rule import travel_rule_logger
    
    str_generator.generate_vda_str(
        txn_id=body.txn_id,
        account_id=body.account_id,
        exchange=body.exchange,
        amount=body.amount,
        score=body.risk_score,
        hold_reason=hold_reason
    )
    
    travel_rule_logger.log_travel_rule(
        txn_id=body.txn_id,
        account_id=body.account_id,
        exchange=body.exchange,
        amount=body.amount
    )

    return alert
