# phase3/core/audit_chain.py

import hashlib
from typing import Optional, List, Dict
import structlog

logger = structlog.get_logger()

# Hardcoded Genesis Previous Hash
GENESIS_PREVIOUS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def calculate_log_hash(
    index: int,
    timestamp: str,
    action: str,
    username: str,
    role: str,
    endpoint: str,
    hashed_id: Optional[str],
    previous_hash: str
) -> str:
    """
    Computes a cryptographic SHA-256 hash representing a single audit log block.
    Ensure formatting is strictly deterministic.
    """
    safe_hashed_id = hashed_id or ""
    data_str = (
        f"{index}|"
        f"{timestamp}|"
        f"{action}|"
        f"{username}|"
        f"{role}|"
        f"{endpoint}|"
        f"{safe_hashed_id}|"
        f"{previous_hash}"
    )
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

def verify_chain_integrity() -> Dict:
    """
    Traverses the database audit logs sequentially to verify hash chain integrity.
    Detects any record deletions, additions, or field modifications.
    """
    from vault.db import vault_db
    logs = vault_db.get_all_audit_logs()
    
    if not logs:
        return {"verified": True, "total_records": 0, "message": "No audit records registered yet."}
        
    expected_prev_hash = GENESIS_PREVIOUS_HASH
    
    for log in logs:
        idx = log["log_index"]
        
        # 1. Verify previous hash matching link
        if log["previous_hash"] != expected_prev_hash:
            logger.error(
                "audit_chain_tamper_detected_link_break", 
                index=idx, 
                expected=expected_prev_hash, 
                found=log["previous_hash"]
            )
            return {
                "verified": False,
                "tampered_index": idx,
                "reason": "Previous hash link broken (link mismatch)",
                "expected": expected_prev_hash,
                "found": log["previous_hash"],
                "record": dict(log)
            }
            
        # 2. Verify current record fields hash integrity
        calculated_hash = calculate_log_hash(
            index=idx,
            timestamp=log["timestamp"],
            action=log["action"],
            username=log["username"],
            role=log["role"],
            endpoint=log["endpoint"],
            hashed_id=log["hashed_id"],
            previous_hash=log["previous_hash"]
        )
        
        if log["current_hash"] != calculated_hash:
            logger.error(
                "audit_chain_tamper_detected_content_altered", 
                index=idx, 
                expected=calculated_hash, 
                found=log["current_hash"]
            )
            return {
                "verified": False,
                "tampered_index": idx,
                "reason": "Log entry fields modified (content altered)",
                "expected": calculated_hash,
                "found": log["current_hash"],
                "record": dict(log)
            }
            
        # Move forward
        expected_prev_hash = log["current_hash"]
        
    logger.info("audit_chain_verification_successful", total_records=len(logs))
    return {
        "verified": True,
        "total_records": len(logs),
        "message": f"Cryptographic integrity verified across all {len(logs)} entries."
    }
