# phase3/api/routes/vault.py

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import os
import structlog
from services.cahv_service import cahv_service
from services.profile_enrichment import get_enriched_profile_summary
from models.vault_models import AccountProfile, VaultFraudAlert
from vault.hash_utils import hash_account_id

# Import security dependencies
from api.middleware.auth_dep import get_current_active_user, RoleChecker

router = APIRouter()
logger = structlog.get_logger()

# Helper function to write audit log entries with user context
def write_audit_log(action: str, hashed_id: str, endpoint: str, user: dict):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.abspath(os.path.join(current_dir, "../../logs"))
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "vault_access.log")
        
        date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        username = user.get("username", "unknown")
        role = user.get("role", "unknown")
        log_line = f"{date_str} action=\"{action}\" user={username} role={role} endpoint={endpoint} hashed_id={hashed_id}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)
            
        # Append to tamper-proof database log chain
        from vault.db import vault_db
        vault_db.append_audit_log(
            timestamp=date_str,
            action=action,
            username=username,
            role=role,
            endpoint=endpoint,
            hashed_id=hashed_id
        )
    except Exception as e:
        logger.error("audit_log_write_failed", error=str(e))

# Pydantic models for request validation
class ProfileCreateRequest(BaseModel):
    account_id: int = Field(..., description="Raw bank account ID")
    name: str = Field(..., description="Customer full name")
    phone: str = Field(..., description="Phone number")
    pan: str = Field(..., description="Permanent Account Number (PAN)")
    email: str = Field(..., description="Customer email address")

class ProfileCreateResponse(BaseModel):
    success: bool
    hashed_id: str

class AlertCreateRequest(BaseModel):
    hashed_id: str = Field(..., description="Hashed identifier of the account")
    risk_score: float = Field(..., ge=0, le=100, description="Composite risk score (0-100)")
    alert_type: str = Field(..., description="Alert sub-type (e.g. MULE_ACCOUNT)")
    category: str = Field(..., description="Alert category (e.g. Transaction Risk)")
    source: str = Field(..., description="Alert originator source (e.g. Fusion Engine)")
    notes: Optional[str] = Field("", description="Investigator notes or execution reasoning")

class AlertCreateResponse(BaseModel):
    success: bool
    alert_id: str

class CaseSummary(BaseModel):
    total_alerts: int
    highest_risk: float
    last_alert: str

class UnifiedVaultResponse(BaseModel):
    profile: AccountProfile
    summary: CaseSummary
    alerts: List[VaultFraudAlert]


@router.get("/vault/account/{hashed_id}", response_model=UnifiedVaultResponse)
async def get_vault_account(hashed_id: str, current_user: dict = Depends(get_current_active_user)):
    # Retrieve profile
    profile_data = cahv_service.get_profile(hashed_id)
    if not profile_data:
        raise HTTPException(status_code=404, detail="Account hash not found in vault")
    
    # Audit log access
    write_audit_log("INVESTIGATOR LOOKUP", hashed_id, "/vault/account", current_user)
    
    # Retrieve alerts and enrich summary
    alerts = cahv_service.get_alerts(hashed_id)
    summary = get_enriched_profile_summary(hashed_id)
    
    # Map alerts to pydantic model format
    is_analyst = current_user.get("role") == "analyst"
    
    pydantic_alerts = []
    for a in alerts:
        pydantic_alerts.append(VaultFraudAlert(
            alert_id=a["alert_id"],
            hashed_id="[REDACTED]" if is_analyst else a["hashed_id"],
            risk_score=a["risk_score"],
            alert_type=a["alert_type"],
            category=a["category"],
            source=a["source"],
            notes=a["notes"],
            created_at=a["created_at"]
        ))
        
    pydantic_profile = AccountProfile(
        hashed_id="[REDACTED]" if is_analyst else profile_data["hashed_id"],
        name=profile_data["name"],
        phone=profile_data["phone"],
        pan=profile_data["pan"],
        email=profile_data["email"],
        created_at=profile_data["created_at"]
    )
    
    pydantic_summary = CaseSummary(
        total_alerts=summary["total_alerts"],
        highest_risk=summary["highest_risk"],
        last_alert=summary["last_alert"]
    )
    
    return UnifiedVaultResponse(
        profile=pydantic_profile,
        summary=pydantic_summary,
        alerts=pydantic_alerts
    )


@router.post("/vault/account", response_model=ProfileCreateResponse)
async def create_vault_account(
    body: ProfileCreateRequest, 
    current_user: dict = Depends(RoleChecker(["admin"]))
):
    # Restricted to Admin
    success = cahv_service.create_profile(
        account_id=body.account_id,
        name=body.name,
        phone=body.phone,
        pan=body.pan,
        email=body.email
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register customer profile in secure vault")
        
    hashed_id = hash_account_id(body.account_id)
    write_audit_log("PROFILE CREATED", hashed_id, "/vault/account", current_user)
    
    return ProfileCreateResponse(success=True, hashed_id=hashed_id)


@router.post("/vault/alert", response_model=AlertCreateResponse)
async def create_vault_alert(
    body: AlertCreateRequest, 
    current_user: dict = Depends(get_current_active_user)
):
    # Access for both Analyst and Admin
    alert_id = cahv_service.create_alert(
        hashed_id=body.hashed_id,
        risk_score=body.risk_score,
        alert_type=body.alert_type,
        category=body.category,
        source=body.source,
        notes=body.notes
    )
    if not alert_id:
        raise HTTPException(status_code=500, detail="Failed to log fraud alert in vault database")
        
    write_audit_log("ALERT CREATED", body.hashed_id, "/vault/alert", current_user)
    
    return AlertCreateResponse(success=True, alert_id=alert_id)


@router.get("/vault/alerts/{hashed_id}", response_model=List[VaultFraudAlert])
async def get_vault_alerts(hashed_id: str, current_user: dict = Depends(get_current_active_user)):
    # Access for both Analyst and Admin
    alerts = cahv_service.get_alerts(hashed_id)
    write_audit_log("ALERTS HISTORY LOOKUP", hashed_id, "/vault/alerts", current_user)
    
    is_analyst = current_user.get("role") == "analyst"
    
    pydantic_alerts = []
    for a in alerts:
        pydantic_alerts.append(VaultFraudAlert(
            alert_id=a["alert_id"],
            hashed_id="[REDACTED]" if is_analyst else a["hashed_id"],
            risk_score=a["risk_score"],
            alert_type=a["alert_type"],
            category=a["category"],
            source=a["source"],
            notes=a["notes"],
            created_at=a["created_at"]
        ))
    return pydantic_alerts
