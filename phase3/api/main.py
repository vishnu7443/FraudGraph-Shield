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
from api.routes import score, cluster, health
from core.fusion_engine import RiskFusionEngine, resolve_path
from core.feature_store import InMemoryFeatureStore
from core.action_engine import ActionEngine

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load all models into memory once
    logger.info("loading_models")
    app.state.fusion_engine = RiskFusionEngine()
    
    # Resolve preprocessor path dynamically to handle multiple start locations
    preprocessor_path = resolve_path("../phase1/models/preprocessor.pkl")
    app.state.feature_store = InMemoryFeatureStore(preprocessor_path)
    
    app.state.action_engine = ActionEngine()
    logger.info("models_loaded")
    yield
    # Shutdown cleanup
    logger.info("shutdown")

app = FastAPI(
    title="FraudGraph Shield API",
    description="Real-time mule account and transaction fraud detection",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_methods=["*"],
    allow_headers=["*"]
)

# Request latency middleware
@app.middleware("http")
async def add_latency_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    latency = (time.perf_counter() - start) * 1000
    response.headers["X-Latency-Ms"] = str(round(latency, 2))
    return response

app.include_router(score.router,   prefix="/api/v1", tags=["Scoring"])
app.include_router(cluster.router, prefix="/api/v1", tags=["Network"])
app.include_router(health.router,  prefix="/api/v1", tags=["Health"])
