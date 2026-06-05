import pytest
import numpy as np
from unittest.mock import MagicMock, patch, AsyncMock
from phase3.core.fusion_engine import RiskFusionEngine

@pytest.fixture
def mock_engine():
    with patch('joblib.load') as mock_joblib_load, \
         patch('shap.TreeExplainer') as mock_shap_explainer, \
         patch('mule_detector.MuleGraphDetector') as mock_detector_class:
         
        # Mock return values for joblib.load
        def side_effect_load(path):
            if "feature_names.pkl" in str(path):
                # return list of 300 features containing required features
                feat_list = ["F" + str(i) for i in range(295)] + ["tenure_days", "product_complexity", "peer_deviation_composite", "F3891", "F3886"]
                return feat_list
            # For other models, return a mock object
            mock_model = MagicMock()
            # mock predict_proba
            mock_model.predict_proba.return_value = np.array([[0.2, 0.8]])
            return mock_model
            
        mock_joblib_load.side_effect = side_effect_load
        
        # Mock explainer
        mock_explainer_inst = MagicMock()
        mock_explainer_inst.shap_values.return_value = [np.zeros((1, 300)), np.zeros((1, 300))]
        mock_shap_explainer.return_value = mock_explainer_inst
        
        # Mock detector
        mock_detector_inst = MagicMock()
        mock_detector_inst.score_account.return_value = 0.45
        mock_detector_class.return_value = mock_detector_inst
        
        # Instantiate engine
        engine = RiskFusionEngine()
        yield engine

def test_compute_cfms_score(mock_engine):
    # No alert
    assert mock_engine.compute_cfms_score(False, "LOW", 0.0) == 0.0
    
    # Fresh alerts (0 hours age)
    assert mock_engine.compute_cfms_score(True, "LOW", 0.0) == 0.5
    assert mock_engine.compute_cfms_score(True, "MEDIUM", 0.0) == 0.8
    assert mock_engine.compute_cfms_score(True, "HIGH", 0.0) == 1.0
    
    # Alert freshness decay (168 hours = 7 days age, should decay to 30%)
    # Decay calculation: base * max(0.3, 1.0 - (age / 168) * 0.7)
    # For age = 168: max(0.3, 1.0 - 0.7) = max(0.3, 0.3) = 0.3
    assert pytest.approx(mock_engine.compute_cfms_score(True, "HIGH", 168.0)) == 0.3
    assert pytest.approx(mock_engine.compute_cfms_score(True, "MEDIUM", 168.0)) == 0.24

def test_fuse_logic(mock_engine):
    # Base composite: LGBM=0.35, GNN=0.40, CFMS=0.25
    # LGBM = 0.5, GNN = 0.5, CFMS = 0.0
    # Composite: (0.35*0.5 + 0.40*0.5 + 0.25*0.0) * 100 = (0.175 + 0.20) * 100 = 37.5
    # Risk tier assignment:
    # < 40: LOW (ALLOW)
    # < 65: MEDIUM (MONITOR)
    # < 80: HIGH (HOLD)
    # >= 80: CRITICAL (BLOCK)
    
    score, tier, action = mock_engine.fuse(0.5, 0.5, 0.0, {})
    assert score == 37.5
    assert tier == "LOW"
    assert action == "ALLOW"
    
    # boosters: is_round_amount (+3), is_new_counterparty (+2), late-night (+4)
    score_boosted, tier_boosted, action_boosted = mock_engine.fuse(0.5, 0.5, 0.0, {
        "is_round_amount": True,
        "is_new_counterparty": True,
        "hour_of_day": 2
    })
    # 37.5 + 3.0 + 2.0 + 4.0 = 46.5
    assert score_boosted == 46.5
    assert tier_boosted == "MEDIUM"
    assert action_boosted == "MONITOR"

@pytest.mark.asyncio
async def test_score_transaction(mock_engine):
    # Mock get_cfms_signal
    mock_engine.get_cfms_signal = AsyncMock(return_value=(True, 24.0, "HIGH"))
    
    # Mock compute_lgbm_score & compute_gnn_score
    mock_engine.compute_lgbm_score = MagicMock(return_value=(0.6, [{"feature_name": "F1", "contribution": 0.1, "direction": "increases_risk"}]))
    mock_engine.compute_gnn_score = MagicMock(return_value=0.7)
    
    features = np.zeros(300)
    transaction_context = {
        "is_round_amount": True,
        "channel": "UPI"
    }
    
    result = await mock_engine.score_transaction(123, features, transaction_context)
    
    assert result["account_id"] == 123
    assert result["lgbm_score"] == 0.6
    assert result["gnn_mule_score"] == 0.7
    assert result["cfms_alert_active"] is True
    assert "composite_score" in result
    assert "risk_tier" in result
    assert "automated_action" in result
