# phase3/api/routes/score.py

from fastapi import APIRouter, Request, HTTPException
from ..models.request import TransactionScoreRequest, BatchScoreRequest
from ..models.response import TransactionScoreResponse, RiskTier, RiskAction
import numpy as np

router = APIRouter()

@router.post("/score", response_model=TransactionScoreResponse)
async def score_transaction(request: Request, body: TransactionScoreRequest):
    engine = request.app.state.fusion_engine
    store  = request.app.state.feature_store
    action_engine = request.app.state.action_engine

    # Get preprocessed features (cache hit or compute)
    features = store.get(body.account_id)
    if features is None:
        raise HTTPException(status_code=404,
            detail=f"Account {body.account_id} not found in feature store. "
                   "Ensure cache is warmed before scoring.")

    transaction_context = {
        "channel": body.channel,
        "is_round_amount": body.is_round_amount,
        "is_new_counterparty": body.is_new_counterparty,
        "hour_of_day": body.hour_of_day,
        "transaction_amount": body.transaction_amount
    }

    result = await engine.score_transaction(body.account_id, features, transaction_context)
    action_engine.execute(body.account_id, result["automated_action"],
                          result["composite_score"], result)

    return TransactionScoreResponse(**result)


@router.post("/score/batch", response_model=list[TransactionScoreResponse])
async def score_batch(request: Request, body: BatchScoreRequest):
    import asyncio
    engine = request.app.state.fusion_engine
    store  = request.app.state.feature_store
    action_engine = request.app.state.action_engine

    async def score_one(req):
        features = store.get(req.account_id)
        if features is None:
            return None
        ctx = {
            "channel": req.channel,
            "is_round_amount": req.is_round_amount,
            "is_new_counterparty": req.is_new_counterparty,
            "hour_of_day": req.hour_of_day,
            "transaction_amount": req.transaction_amount
        }
        result = await engine.score_transaction(req.account_id, features, ctx)
        action_engine.execute(req.account_id, result["automated_action"],
                              result["composite_score"], result)
        return TransactionScoreResponse(**result)

    tasks = [score_one(req) for req in body.requests]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]
