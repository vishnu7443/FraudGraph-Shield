# phase3/api/routes/audit.py

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import structlog

from vault.db import vault_db
from core.audit_chain import verify_chain_integrity
from api.middleware.auth_dep import get_current_active_user, RoleChecker

router = APIRouter()
logger = structlog.get_logger()

class TamperRequest(BaseModel):
    log_index: int = Field(..., description="The log sequence number (log_index) to compromise")
    tampered_username: str = Field("attacker_fiu_portal", description="Malicious username to inject")

class AuditLogResponse(BaseModel):
    log_index: int
    timestamp: str
    action: str
    username: str
    role: str
    endpoint: str
    hashed_id: Optional[str]
    previous_hash: str
    current_hash: str


@router.get("/audit/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(current_user: dict = Depends(RoleChecker(["admin"]))):
    """
    Retrieves the entire audit trail ledger from the database.
    Restricted to Admin role only.
    """
    logs = vault_db.get_all_audit_logs()
    logger.info("audit_logs_retrieved", count=len(logs), requester=current_user.get("username"))
    return logs


@router.get("/audit/verify")
async def verify_audit_trail(current_user: dict = Depends(get_current_active_user)):
    """
    Runs sequential cryptographic verification across the entire audit log chain.
    """
    result = verify_chain_integrity()
    logger.info(
        "audit_chain_verification_run", 
        requester=current_user.get("username"), 
        verified=result["verified"]
    )
    return result


@router.post("/audit/simulate-tamper")
async def simulate_tamper(body: TamperRequest, current_user: dict = Depends(get_current_active_user)):
    """
    Intentionally alters a past log record's username to demonstrate validation engine alerts.
    Accessible to both Analyst and Admin roles for hackathon presentation simplicity.
    """
    # Verify that the target log exists
    logs = vault_db.get_all_audit_logs()
    matching_log = next((l for l in logs if l["log_index"] == body.log_index), None)
    
    if not matching_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log entry at index {body.log_index} not found."
        )
        
    original_user = matching_log["username"]
    success = vault_db.tamper_audit_log_record(body.log_index, body.tampered_username)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to simulate tampering inside SQLite database"
        )
        
    logger.warn(
        "audit_chain_tamper_simulated",
        index=body.log_index,
        original_user=original_user,
        tampered_user=body.tampered_username,
        actor=current_user.get("username")
    )
    return {
        "success": True,
        "message": f"Simulated tampering on record #{body.log_index}.",
        "details": {
            "log_index": body.log_index,
            "original_username": original_user,
            "tampered_username": body.tampered_username
        }
    }
