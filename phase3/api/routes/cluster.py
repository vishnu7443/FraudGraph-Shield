# phase3/api/routes/cluster.py

from fastapi import APIRouter, Request, HTTPException
import numpy as np
from ..models.request import ClusterRequest
from ..models.response import ClusterResponse, ClusterNode, RiskTier

router = APIRouter()

@router.post("/cluster", response_model=ClusterResponse)
async def get_cluster(request: Request, body: ClusterRequest):
    detector = request.app.state.fusion_engine.detector

    try:
        cluster_nodes = detector.get_cluster(body.account_id, hop=body.hop_depth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not cluster_nodes:
        raise HTTPException(status_code=404,
            detail=f"No cluster found for account {body.account_id}")

    nodes_response = []
    for node_id in cluster_nodes:
        # Retrieve scaled features from graph pyg_data and unscale them to avoid double-scaling inside score_account
        scaled_features = detector.pyg_data.x[node_id].cpu().numpy().reshape(1, -1)
        unscaled_features = detector.scaler.inverse_transform(scaled_features)[0]
        
        mule_score = float(detector.score_account(node_id, unscaled_features))
        
        tier = ("CRITICAL" if mule_score > 0.8 else
                "HIGH"     if mule_score > 0.65 else
                "MEDIUM"   if mule_score > 0.4 else "LOW")
        nodes_response.append(ClusterNode(
            account_id=node_id,
            mule_score=round(mule_score, 4),
            account_type="Unknown",  # enriched in Phase 4 from dataset
            risk_tier=RiskTier(tier)
        ))

    cluster_risk = max(n.mule_score for n in nodes_response) if nodes_response else 0.0
    relay_detected = any(n.mule_score > 0.7 for n in nodes_response)

    return ClusterResponse(
        root_account_id=body.account_id,
        cluster_nodes=nodes_response,
        cluster_risk_score=round(cluster_risk, 4),
        relay_chain_detected=relay_detected
    )
