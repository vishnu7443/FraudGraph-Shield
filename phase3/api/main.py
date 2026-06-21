# phase3/api/main.py

import sys
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import structlog

# Add phase3 directory to sys.path to ensure modules under api and core are resolvable
current_dir = os.path.dirname(os.path.abspath(__file__))
phase3_dir = os.path.abspath(os.path.join(current_dir, ".."))
if phase3_dir not in sys.path:
    sys.path.append(phase3_dir)

# Import routes, engine, store and action engine
from api.routes import score, cluster, health, crypto, vault, auth, audit
from core.fusion_engine import RiskFusionEngine, resolve_path
from core.feature_store import InMemoryFeatureStore
from core.action_engine import ActionEngine

logger = structlog.get_logger()


def create_app(
    engine=None,
    feature_store=None,
    action_engine=None,
) -> FastAPI:
    """Factory function to create the FastAPI app. Accepts optional pre-built
    dependencies so tests can inject mocks without loading real models."""

    application = FastAPI(
        title="FraudGraph Shield API",
        description="Real-time mule account and transaction fraud detection",
        version="1.0.0"
    )

    # Initialize application state — use provided objects or create real ones
    if engine is None:
        logger.info("loading_models")
        engine = RiskFusionEngine()
    if feature_store is None:
        preprocessor_path = resolve_path("../phase1/models/preprocessor.pkl")
        feature_store = InMemoryFeatureStore(preprocessor_path)
    if action_engine is None:
        action_engine = ActionEngine()

    application.state.fusion_engine = engine
    application.state.feature_store = feature_store
    application.state.action_engine = action_engine
    logger.info("models_loaded")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("startup_complete")
        yield
        logger.info("shutdown")

    application.router.lifespan_context = lifespan

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # restrict in production
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Request latency middleware
    @application.middleware("http")
    async def add_latency_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        latency = (time.perf_counter() - start) * 1000
        response.headers["X-Latency-Ms"] = str(round(latency, 2))
        return response

    application.include_router(score.router,   prefix="/api/v1", tags=["Scoring"])
    application.include_router(cluster.router, prefix="/api/v1", tags=["Network"])
    application.include_router(health.router,  prefix="/api/v1", tags=["Health"])
    application.include_router(crypto.router,  prefix="/api/v1", tags=["Crypto"])
    application.include_router(vault.router,   prefix="/api/v1", tags=["Vault"])
    application.include_router(auth.router,    prefix="/api/v1", tags=["Auth"])
    application.include_router(audit.router,   prefix="/api/v1", tags=["Audit"])

    return application



# Module-level app for uvicorn: `uvicorn api.main:app`
# This only runs when the module is imported for the first time with real models.
app = create_app()
