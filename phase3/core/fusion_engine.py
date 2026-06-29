# phase3/core/fusion_engine.py

import numpy as np
import joblib
import structlog
import httpx
from typing import Tuple, List, Optional
import os
import sys
import asyncio
import time

# Import crypto detector, config, db, models, and logging generators
from services.crypto_detector import detector
from core.config import settings
from storage.db import db_instance
from models.crypto_alert import CryptoAlert
from services.str_generator import str_generator
from services.travel_rule import travel_rule_logger
from vault.hash_utils import hash_account_id
from services.cahv_service import cahv_service


# Dynamically add phase1 and phase2 directories to sys.path using absolute paths
current_dir = os.path.dirname(os.path.abspath(__file__))
phase1_dir = os.path.abspath(os.path.join(current_dir, "../../phase1"))
phase2_dir = os.path.abspath(os.path.join(current_dir, "../../phase2"))

if phase1_dir not in sys.path:
    sys.path.append(phase1_dir)
if phase2_dir not in sys.path:
    sys.path.append(phase2_dir)

logger = structlog.get_logger()

def resolve_path(path_str: str) -> str:
    """Resolves a relative path to an absolute path, checking multiple base locations."""
    if not path_str:
        return path_str
    if os.path.isabs(path_str):
        return path_str
    # 1. Check relative to current working directory
    if os.path.exists(path_str):
        return os.path.abspath(path_str)
    # 2. Check relative to phase3/ directory
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    resolved = os.path.abspath(os.path.join(base_dir, path_str))
    if os.path.exists(resolved):
        return resolved
    # 3. Check relative to workspace root (parent of phase3/)
    root_dir = os.path.abspath(os.path.join(base_dir, ".."))
    resolved_root = os.path.abspath(os.path.join(root_dir, path_str))
    if os.path.exists(resolved_root):
        return resolved_root
    return resolved

class RiskFusionEngine:
    # Fusion weights — tuned during validation
    # CFMS alert is the strongest single signal
    W_LGBM   = 0.35
    W_GNN    = 0.40
    W_CFMS   = 0.25

    # Severity multipliers for CFMS alert
    CFMS_SEVERITY_WEIGHTS = {"LOW": 0.5, "MEDIUM": 0.8, "HIGH": 1.0}

    def __init__(self):
        # Load environment variables in case they are not loaded yet
        from dotenv import load_dotenv
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        load_dotenv(os.path.join(base_dir, ".env"))

        # Lazy imports of native libraries to prevent DLL initialization routines from failing on load
        import shap
        if os.getenv("VERCEL"):
            logger.warning("Running on Vercel: Using Mock GNN Detector to avoid PyTorch 500MB limit")
            class MockDetector:
                def score_account(self, aid, f):
                    import hashlib
                    return float((int(hashlib.sha256(str(aid).encode()).hexdigest(), 16) % 80) / 100.0 + 0.1)
                def get_cluster(self, aid, hop=2):
                    return [aid + 1, aid + 2]
            self.detector = MockDetector()
        else:
            from mule_detector import MuleGraphDetector
            gnn_path = resolve_path(os.getenv("GNN_MODEL_PATH", "../phase2/models/gnn_model.pt"))
            graph_path = resolve_path(os.getenv("GRAPH_DATA_PATH", "../phase2/models/graph_data.pt"))
            scaler_path = resolve_path("../phase2/models/gnn_scaler.pkl")
            self.detector = MuleGraphDetector(
                model_path=gnn_path,
                scaler_path=scaler_path,
                graph_path=graph_path
            )
        self.cfms_url = os.getenv("CFMS_MOCK_URL", "http://localhost:8001")
        logger.info("fusion_engine_initialized")

    async def get_cfms_signal(self, account_id: int) -> Tuple[bool, float, str]:
        """Returns (alert_active, alert_age_hours, severity)"""
        try:
            async with httpx.AsyncClient(timeout=0.5) as client:
                resp = await client.get(f"{self.cfms_url}/cfms/alert/{account_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    if data["alert_active"]:
                        return True, data.get("alert_age_hours", 0), data.get("severity", "LOW")
                return False, 0.0, "NONE"
        except Exception as e:
            logger.warning("cfms_unreachable", error=str(e))
            return False, 0.0, "NONE"  # graceful degradation

    def assemble_gnn_features(self, account_id: int, features: np.ndarray, lgbm_score: float) -> np.ndarray:
        """Assembles 74-dimensional GNN features from 300-dimensional preprocessed features."""
        if len(features) == 74:
            return features
            
        if os.getenv("VERCEL"):
            return np.zeros(74)
            
        # Extract mean and scale from detector's scaler for unscaling
        mean = self.detector.scaler.mean_
        scale = self.detector.scaler.scale_
        
        # Read the existing scaled features for this node in the graph
        scaled_node = self.detector.pyg_data.x[account_id].cpu().numpy()
        
        # Index mappings of features to pull from graph
        idx_cs = 69
        idx_thvs1 = 70
        idx_thvs2 = 71
        idx_high_vel = 73
        
        # Unscale variables
        unscaled_cs = scaled_node[idx_cs] * scale[idx_cs] + mean[idx_cs]
        unscaled_thvs1 = scaled_node[idx_thvs1] * scale[idx_thvs1] + mean[idx_thvs1]
        unscaled_thvs2 = scaled_node[idx_thvs2] * scale[idx_thvs2] + mean[idx_thvs2]
        unscaled_high_vel = scaled_node[idx_high_vel] * scale[idx_high_vel] + mean[idx_high_vel]
        
        # Extract engineered features from the preprocessed feature vector
        tenure = features[self.feature_names.index('tenure_days')]
        complexity = features[self.feature_names.index('product_complexity')]
        peer_dev = features[self.feature_names.index('peer_deviation_composite')]
        occ_encoded = features[self.feature_names.index('F3891')]
        acc_encoded = features[self.feature_names.index('F3886')]
        
        # Re-assemble 74-dimensional node feature vector
        node_features = np.concatenate([
            features[:64],
            np.array([tenure, complexity, peer_dev, occ_encoded, acc_encoded, unscaled_cs]),
            np.array([unscaled_thvs1, unscaled_thvs2]),
            np.array([lgbm_score]),
            np.array([unscaled_high_vel])
        ])
        
        return node_features

    def compute_lgbm_score(self, features: np.ndarray) -> Tuple[float, List[dict]]:
        """Returns (score_0_to_1, shap_explanations)"""
        score = float(self.lgbm_model.predict_proba(features.reshape(1, -1))[0][1])

        import shap
        shap_vals = self.lgbm_explainer.shap_values(features.reshape(1, -1))
        # Handle different structures of shap_values depending on the shap library version
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]  # binary classification positive class
        elif len(shap_vals.shape) == 3:
            shap_vals = shap_vals[:, :, 1] # SHAP 0.45+ output format for classification
            
        # Extract the shap values row
        row_shap = shap_vals[0] if len(shap_vals.shape) > 1 else shap_vals

        # Top 5 SHAP factors
        importance_idx = np.argsort(np.abs(row_shap))[::-1][:5]
        explanations = []
        for idx in importance_idx:
            explanations.append({
                "feature_name": self.feature_names[idx],
                "contribution": round(float(row_shap[idx]), 4),
                "direction": "increases_risk" if row_shap[idx] > 0 else "decreases_risk"
            })
        return score, explanations

    def compute_gnn_score(self, account_id: int, features: np.ndarray, lgbm_score: float = None) -> float:
        if len(features) != 74 and lgbm_score is None:
            lgbm_score, _ = self.compute_lgbm_score(features)
        gnn_features = self.assemble_gnn_features(account_id, features, lgbm_score)
        return float(self.detector.score_account(account_id, gnn_features))

    def compute_cfms_score(self, alert_active: bool, severity: str, age_hours: float) -> float:
        if not alert_active:
            return 0.0
        base = self.CFMS_SEVERITY_WEIGHTS.get(severity, 0.5)
        # Alert freshness decay — older alerts carry less weight
        # Fully weighted if under 24 hours, decays to 30% at 7 days
        freshness = max(0.3, 1.0 - (age_hours / 168) * 0.7)
        return base * freshness

    def fuse(
        self,
        lgbm_score: float,
        gnn_score: float,
        cfms_score: float,
        transaction_context: dict
    ) -> Tuple[float, str, str]:
        """
        Returns (composite_score_0_to_100, risk_tier, automated_action)
        """
        # Base composite
        composite = (
            self.W_LGBM * lgbm_score +
            self.W_GNN  * gnn_score  +
            self.W_CFMS * cfms_score
        ) * 100

        # Transaction context boosters
        if transaction_context.get("is_round_amount"):
            composite += 3.0
        if transaction_context.get("is_new_counterparty"):
            composite += 2.0
        if transaction_context.get("hour_of_day") in [0,1,2,3,4]:
            composite += 4.0  # Late-night transactions are higher risk
        if transaction_context.get("channel") == "UPI" and lgbm_score > 0.6:
            composite += 3.0

        composite = min(100.0, max(0.0, composite))

        # Tier and action assignment
        low_t    = float(os.getenv("FUSION_THRESHOLD_MEDIUM", 40))
        med_t    = float(os.getenv("FUSION_THRESHOLD_HIGH", 65))
        high_t   = float(os.getenv("FUSION_THRESHOLD_CRITICAL", 80))

        if composite < low_t:
            return composite, "LOW", "ALLOW"
        elif composite < med_t:
            return composite, "MEDIUM", "MONITOR"
        elif composite < high_t:
            return composite, "HIGH", "HOLD"
        else:
            return composite, "CRITICAL", "BLOCK"

    async def process_crypto_alert(
        self,
        account_id: int,
        exchange: str,
        amount: float,
        score: float,
        txn_id: str
    ):
        try:
            # 1. Determine severity based on config thresholds
            if score >= settings.SEVERITY_THRESHOLD_CRITICAL:
                severity = "CRITICAL"
            elif score >= settings.SEVERITY_THRESHOLD_HIGH:
                severity = "HIGH"
            elif score >= settings.SEVERITY_THRESHOLD_MEDIUM:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            hold_reason = f"Funds exiting to high-risk VDA provider {exchange}"
            alert_id = f"ALT-{account_id}-{int(time.time())}"
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            # 2. Create alert object
            alert = CryptoAlert(
                alert_id=alert_id,
                txn_id=txn_id,
                account_id=account_id,
                exchange=exchange,
                amount=amount,
                risk_score=score,
                severity=severity,
                hold_reason=hold_reason,
                timestamp=timestamp,
                status="OPEN"
            )

            # 3. Save to database
            db_instance.save_alert(alert)

            # 4. Generate STR Report
            str_generator.generate_vda_str(
                txn_id=txn_id,
                account_id=account_id,
                exchange=exchange,
                amount=amount,
                score=score,
                hold_reason=hold_reason
            )

            # 5. Log Travel Rule
            travel_rule_logger.log_travel_rule(
                txn_id=txn_id,
                account_id=account_id,
                exchange=exchange,
                amount=amount
            )
            
            logger.info("crypto_alert_background_processing_done", alert_id=alert_id)
        except Exception as e:
            logger.error("crypto_alert_background_processing_failed", error=str(e))

    async def score_transaction(
        self,
        account_id: int,
        features: np.ndarray,
        transaction_context: dict
    ) -> dict:
        import asyncio, time
        start = time.perf_counter()

        # Run CFMS check concurrently with model inference
        cfms_task = asyncio.create_task(self.get_cfms_signal(account_id))

        lgbm_score, shap_explanations = self.compute_lgbm_score(features)
        gnn_score = self.compute_gnn_score(account_id, features, lgbm_score)

        alert_active, alert_age_hours, severity = await cfms_task
        cfms_score = self.compute_cfms_score(alert_active, severity, alert_age_hours)

        composite, risk_tier, action = self.fuse(
            lgbm_score, gnn_score, cfms_score, transaction_context
        )

        # Check for crypto exit detection
        crypto_detected = False
        exchange_name = None
        confidence = 0.0
        dest_name = transaction_context.get("destination_name")
        if dest_name:
            crypto_res = detector.detect_crypto(dest_name)
            if crypto_res["is_crypto"]:
                crypto_detected = True
                exchange_name = crypto_res["exchange"]
                confidence = crypto_res["confidence"]
                if composite > 40.0:
                    composite += crypto_res["risk_boost"]
                    composite = min(100.0, composite)
                
                # Apply Force HOLD logic
                action = "HOLD"
                if risk_tier in ["LOW", "MEDIUM"]:
                    risk_tier = "HIGH"

        # Spawn background task if crypto is detected
        if crypto_detected and exchange_name:
            txn_id = f"TXN-{account_id}-{int(time.time())}"
            asyncio.create_task(
                self.process_crypto_alert(
                    account_id=account_id,
                    exchange=exchange_name,
                    amount=transaction_context.get("transaction_amount", 0.0),
                    score=composite,
                    txn_id=txn_id
                )
            )
            logger.warning(
                f"Crypto exit detected: {exchange_name}",
                exchange=exchange_name,
                txn_id=txn_id,
                risk_score=round(composite, 2),
                action=action
            )

        # Trigger CAHV alert automatically if risk score exceeds threshold
        if composite > settings.VAULT_ALERT_THRESHOLD:
            hashed_id = hash_account_id(account_id)
            cahv_service.create_alert(
                hashed_id=hashed_id,
                risk_score=composite,
                alert_type="FUSION_ENGINE_ALERT",
                category="Transaction Risk",
                source="Fusion Engine",
                notes=f"Automated risk threshold breach: score={composite:.2f}, tier={risk_tier}, action={action}"
            )


        latency_ms = (time.perf_counter() - start) * 1000

        logger.info("transaction_scored",
            account_id=account_id,
            composite=round(composite, 2),
            risk_tier=risk_tier,
            action=action,
            latency_ms=round(latency_ms, 2)
        )

        return {
            "account_id": account_id,
            "composite_score": round(composite, 2),
            "risk_tier": risk_tier,
            "automated_action": action,
            "lgbm_score": round(lgbm_score, 4),
            "gnn_mule_score": round(gnn_score, 4),
            "cfms_alert_active": alert_active,
            "cfms_alert_age_hours": alert_age_hours if alert_active else None,
            "top_shap_factors": shap_explanations,
            "inference_latency_ms": round(latency_ms, 2),
            "model_version": "v1.0.0",
            "crypto_detected": crypto_detected,
            "crypto_exchange": exchange_name,
            "crypto_confidence": confidence
        }

