# phase3/api/routes/health.py

from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/health")
async def health(request: Request):
    store_ok = request.app.state.feature_store.health_check()
    return {
        "status": "ok" if store_ok else "degraded",
        "feature_store": "ok" if store_ok else "unavailable",
        "models": "loaded"
    }
