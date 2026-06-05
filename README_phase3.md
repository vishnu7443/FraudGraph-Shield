# FraudGraph Shield — Phase 3: Risk Fusion Engine + FastAPI Scoring Endpoint

## Overview

Phase 3 takes the two independently trained models from Phase 1 (LightGBM transaction scorer) and Phase 2 (GraphSAGE mule detector) and wraps them behind a **production-grade FastAPI backend** that fuses their outputs into a single composite risk score with automated action assignment.

### Architecture

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  LightGBM    │     │  GraphSAGE    │     │  CFMS Mock   │
│  Phase 1     │     │  Phase 2      │     │  (port 8001) │
│  score 0–1   │     │  score 0–1    │     │  alert feed  │
└──────┬───────┘     └──────┬────────┘     └──────┬───────┘
       │                    │                     │
       └────────────┬───────┘─────────────────────┘
                    ▼
          ┌─────────────────┐
          │  Risk Fusion    │  W_LGBM=0.35 · W_GNN=0.40 · W_CFMS=0.25
          │  Engine         │  + context boosters
          └────────┬────────┘
                   ▼
          ┌─────────────────┐
          │  Action Engine  │  ALLOW / MONITOR / HOLD / BLOCK
          └────────┬────────┘
                   ▼
          ┌─────────────────┐
          │  FastAPI        │  /api/v1/score   POST
          │  (port 8000)    │  /api/v1/score/batch  POST
          │                 │  /api/v1/cluster POST
          │                 │  /api/v1/health  GET
          └─────────────────┘
```

## Quick Start

### Option 1: Docker (recommended for demo)

```bash
cd phase3/docker
docker-compose up --build
```

This starts three containers:
- **API** on port `8000`
- **CFMS Mock** on port `8001`
- **Redis** on port `6379`

### Option 2: Local development

```bash
# 1. Activate virtual environment
.venv\Scripts\activate    # Windows
source .venv/bin/activate  # Linux/Mac

# 2. Start CFMS Mock (separate terminal)
uvicorn phase3.core.cfms_mock:cfms_app --port 8001

# 3. Start main API
cd phase3
uvicorn api.main:app --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/score` | Score a single transaction |
| POST | `/api/v1/score/batch` | Score up to 100 transactions concurrently |
| POST | `/api/v1/cluster` | Retrieve co-suspicious account network |
| GET | `/api/v1/health` | Check API and model health |

### Example: Score a Transaction

```bash
curl -X POST http://localhost:8000/api/v1/score \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 42,
    "transaction_amount": 50000.0,
    "channel": "UPI",
    "is_new_counterparty": true,
    "is_round_amount": true,
    "hour_of_day": 2
  }'
```

### Example Response

```json
{
  "account_id": 42,
  "composite_score": 72.3,
  "risk_tier": "HIGH",
  "automated_action": "HOLD",
  "lgbm_score": 0.65,
  "gnn_mule_score": 0.78,
  "cfms_alert_active": true,
  "cfms_alert_age_hours": 12.5,
  "top_shap_factors": [
    {"feature_name": "F123", "contribution": 0.15, "direction": "increases_risk"},
    {"feature_name": "F456", "contribution": -0.08, "direction": "decreases_risk"}
  ],
  "inference_latency_ms": 89.2,
  "model_version": "v1.0.0"
}
```

## Risk Tiers & Automated Actions

| Composite Score | Tier | Action | What Happens |
|-----------------|------|--------|-------------|
| 0 – 39 | LOW | ALLOW | Transaction cleared |
| 40 – 64 | MEDIUM | MONITOR | Cleared, flagged for 4-hour review |
| 65 – 79 | HIGH | HOLD | Held 15 min, TMS alert generated |
| 80 – 100 | CRITICAL | BLOCK | Frozen, STR filed, URGENT queue |

All thresholds are configurable via environment variables (`FUSION_THRESHOLD_MEDIUM`, `FUSION_THRESHOLD_HIGH`, `FUSION_THRESHOLD_CRITICAL`).

## Context Boosters

The fusion engine applies additive bonuses based on transaction context:

| Condition | Boost |
|-----------|-------|
| Round amount (₹10000, ₹50000, etc.) | +3 |
| New counterparty | +2 |
| Late-night (00:00 – 04:59) | +4 |
| UPI channel + LightGBM score > 0.6 | +3 |

## CFMS Alert Integration

The CFMS Mock API simulates government I4C/FIU-IND alert feeds:
- ~15% of 9,082 accounts have active alerts
- Alert freshness decays over 7 days (100% → 30% weight)
- Severity levels: LOW (0.5), MEDIUM (0.8), HIGH (1.0)
- 0.5s hard timeout with graceful degradation — scoring works even if CFMS is down

## Running Tests

```bash
# All tests
pytest

# Specific test suites
pytest phase3/tests/test_fusion.py -v        # Fusion logic
pytest phase3/tests/test_endpoints.py -v     # API endpoints
pytest phase3/tests/test_latency.py -v -s    # P99 latency benchmark
pytest phase3/tests/test_api.py -v           # API integration (TestClient)
```

## Performance

- **P50 latency**: < 30ms (mocked engine)
- **P99 latency**: < 350ms target
- **Batch throughput**: 100 concurrent accounts
- Models load **once** at startup via FastAPI lifespan — never per-request

## Project Structure

```
phase3/
├── api/
│   ├── main.py              # FastAPI app, lifespan, middleware
│   ├── models/
│   │   ├── request.py       # Pydantic request schemas
│   │   └── response.py      # Pydantic response schemas
│   └── routes/
│       ├── score.py          # /score, /score/batch
│       ├── cluster.py        # /cluster
│       └── health.py         # /health
├── core/
│   ├── fusion_engine.py      # Risk Fusion Engine (LightGBM + GNN + CFMS)
│   ├── action_engine.py      # Post-scoring action dispatcher
│   ├── feature_store.py      # Redis + InMemory feature store
│   └── cfms_mock.py          # Government alert mock API
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── postman/
│   └── FraudGraph_Shield_API.postman_collection.json
├── tests/
│   ├── test_api.py           # API integration tests (TestClient)
│   ├── test_endpoints.py     # API tests (httpx AsyncClient)
│   ├── test_fusion.py        # Fusion logic unit tests
│   ├── test_fusion_engine.py # Engine mock tests
│   ├── test_latency.py       # P99 latency benchmark
│   ├── test_cfms_mock.py     # CFMS Mock API tests
│   └── ...                   # Phase 1/2 regression tests
├── requirements_phase3.txt
└── .env
```

## Environment Configuration

All tuning parameters are in `phase3/.env`:

```env
LGBM_MODEL_PATH=../phase1/models/lgbm_model.pkl
GNN_MODEL_PATH=../phase2/models/gnn_model.pt
GRAPH_DATA_PATH=../phase2/models/graph_data.pt
REDIS_URL=redis://localhost:6379
CFMS_MOCK_URL=http://localhost:8001
FUSION_THRESHOLD_MEDIUM=40
FUSION_THRESHOLD_HIGH=65
FUSION_THRESHOLD_CRITICAL=80
LOG_LEVEL=INFO
```

To change a threshold, update `.env` and restart — no code change required.
