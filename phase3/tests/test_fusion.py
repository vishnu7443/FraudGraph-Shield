# phase3/tests/test_fusion.py
#
# Direct fusion-logic tests that exercise RiskFusionEngine.fuse() and
# RiskFusionEngine.compute_cfms_score() without loading real models.
# We patch __init__ to skip model loading entirely.

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import numpy as np
from unittest.mock import patch, MagicMock
from phase3.core.fusion_engine import RiskFusionEngine


@pytest.fixture
def engine():
    """Create a RiskFusionEngine with __init__ completely bypassed."""
    with patch.object(RiskFusionEngine, '__init__', lambda self: None):
        eng = RiskFusionEngine()
        # Manually set the class-level attributes (normally set by the class body)
        eng.W_LGBM = 0.35
        eng.W_GNN = 0.40
        eng.W_CFMS = 0.25
        eng.CFMS_SEVERITY_WEIGHTS = {"LOW": 0.5, "MEDIUM": 0.8, "HIGH": 1.0}
        yield eng


def test_low_scores_produce_allow_action(engine):
    composite, tier, action = engine.fuse(0.1, 0.05, 0.0, {})
    assert action == "ALLOW"
    assert tier == "LOW"


def test_high_scores_produce_block_action(engine):
    composite, tier, action = engine.fuse(0.95, 0.90, 1.0, {})
    assert action == "BLOCK"
    assert tier == "CRITICAL"


def test_cfms_alert_escalates_score(engine):
    """Adding a CFMS signal should increase composite score."""
    c1, t1, _ = engine.fuse(0.45, 0.40, 0.0, {})
    c2, t2, _ = engine.fuse(0.45, 0.40, 1.0, {})
    assert c2 > c1
    # With CFMS=1.0 boost, score should be significantly higher
    assert c2 - c1 > 20  # 25% * 1.0 * 100 = +25 points


def test_cfms_pushes_medium_to_high(engine):
    """Using high enough base scores + CFMS should cross into HIGH tier."""
    c_no_cfms, t_no_cfms, _ = engine.fuse(0.60, 0.55, 0.0, {})
    c_with_cfms, t_with_cfms, _ = engine.fuse(0.60, 0.55, 1.0, {})
    assert t_no_cfms in ["LOW", "MEDIUM"]
    assert t_with_cfms in ["HIGH", "CRITICAL"]


def test_composite_score_in_range(engine):
    rng = np.random.default_rng(42)
    for _ in range(100):
        l, g, c = rng.random(), rng.random(), rng.random()
        score, _, _ = engine.fuse(l, g, c, {})
        assert 0.0 <= score <= 100.0


def test_late_night_transaction_boosts_score(engine):
    day_ctx = {"hour_of_day": 14}
    night_ctx = {"hour_of_day": 2}
    score_day, _, _ = engine.fuse(0.5, 0.5, 0.0, day_ctx)
    score_night, _, _ = engine.fuse(0.5, 0.5, 0.0, night_ctx)
    assert score_night > score_day


def test_weights_sum_to_one(engine):
    total = engine.W_LGBM + engine.W_GNN + engine.W_CFMS
    assert abs(total - 1.0) < 1e-9


def test_cfms_freshness_decay(engine):
    fresh = engine.compute_cfms_score(True, "HIGH", 1.0)
    stale = engine.compute_cfms_score(True, "HIGH", 144.0)
    assert fresh > stale
