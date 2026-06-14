import structlog
from typing import Dict
from services.cahv_service import cahv_service

logger = structlog.get_logger()

def get_enriched_profile_summary(hashed_id: str) -> Dict:
    """
    Aggregates threat alerts history to summarize key risk metrics for investigator UI.
    """
    try:
        alerts = cahv_service.get_alerts(hashed_id)
        if not alerts:
            return {
                "total_alerts": 0,
                "highest_risk": 0.0,
                "last_alert": "NEVER"
            }
            
        total_alerts = len(alerts)
        highest_risk = max(a.get("risk_score", 0.0) for a in alerts)
        
        # Alerts are ordered by created_at DESC in database, so first is latest
        last_alert = alerts[0].get("created_at", "UNKNOWN")
        
        return {
            "total_alerts": total_alerts,
            "highest_risk": round(highest_risk, 1),
            "last_alert": last_alert
        }
    except Exception as e:
        logger.error("profile_enrichment_failed", hashed_id=hashed_id, error=str(e))
        return {
            "total_alerts": 0,
            "highest_risk": 0.0,
            "last_alert": "ERROR"
        }
