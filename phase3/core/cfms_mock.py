# phase3/core/cfms_mock.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import random
import time

# Set a random seed to make the mock alerts registry deterministic for testing
random.seed(42)

cfms_app = FastAPI(title="CFMS Mock API", version="1.0")

# Simulate ~15% of accounts having active CFMS alerts
# In reality this would query the I4C database
MOCK_ALERT_REGISTRY = {
    acc_id: {
        "alert_active": True,
        "ticket_id": f"CFMS2024{acc_id:06d}",
        "fraud_type": random.choice(["UPI_FRAUD", "PHISHING", "MULE_ACCOUNT", "SIM_SWAP"]),
        "registered_at": time.time() - random.randint(3600, 86400 * 7),
        "severity": random.choice(["LOW", "MEDIUM", "HIGH"]),
        "reporting_bank": random.choice(["SBI", "PNB", "HDFC", "ICICI", "BOI"])
    }
    for acc_id in random.sample(range(9082), int(9082 * 0.15))
}

class CFMSAlertResponse(BaseModel):
    account_id: int
    alert_active: bool
    ticket_id: Optional[str] = None
    fraud_type: Optional[str] = None
    alert_age_hours: Optional[float] = None
    severity: Optional[str] = None
    reporting_bank: Optional[str] = None

@cfms_app.get("/cfms/alert/{account_id}", response_model=CFMSAlertResponse)
async def get_cfms_alert(account_id: int):
    if account_id in MOCK_ALERT_REGISTRY:
        alert = MOCK_ALERT_REGISTRY[account_id]
        age_hours = (time.time() - alert["registered_at"]) / 3600
        return CFMSAlertResponse(
            account_id=account_id,
            alert_active=True,
            ticket_id=alert["ticket_id"],
            fraud_type=alert["fraud_type"],
            alert_age_hours=round(age_hours, 2),
            severity=alert["severity"],
            reporting_bank=alert["reporting_bank"]
        )
    return CFMSAlertResponse(account_id=account_id, alert_active=False)

@cfms_app.get("/cfms/health")
async def cfms_health():
    return {"status": "ok", "registry_size": len(MOCK_ALERT_REGISTRY)}
