from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum

class RiskAction(str, Enum):
    ALLOW = "ALLOW"
    MONITOR = "MONITOR"
    HOLD = "HOLD"
    BLOCK = "BLOCK"

class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SHAPExplanation(BaseModel):
    feature_name: str
    contribution: float
    direction: str  # "increases_risk" or "decreases_risk"

class TransactionScoreResponse(BaseModel):
    account_id: int
    composite_score: float          # 0-100
    risk_tier: RiskTier
    automated_action: RiskAction
    lgbm_score: float               # 0-1 raw
    gnn_mule_score: float           # 0-1 raw
    cfms_alert_active: bool
    cfms_alert_age_hours: Optional[float]
    top_shap_factors: List[SHAPExplanation]  # top 5
    inference_latency_ms: float
    model_version: str

class ClusterNode(BaseModel):
    account_id: int
    mule_score: float
    account_type: str
    risk_tier: RiskTier

class ClusterResponse(BaseModel):
    root_account_id: int
    cluster_nodes: List[ClusterNode]
    cluster_risk_score: float       # max mule score in cluster
    relay_chain_detected: bool      # True if any node has score > 0.7
