# phase4/dashboard/demo_data.py
#
# Pre-baked demo data representing transactions, risk queues, SHAP values, and GraphSAGE clusters.
# Used by api_client.py as an offline fallback when the FastAPI service is not running.

DEMO_SCORES = {
    0: {
        "account_id": 0,
        "composite_score": 12.5,
        "risk_tier": "LOW",
        "automated_action": "ALLOW",
        "lgbm_score": 0.12,
        "gnn_mule_score": 0.08,
        "cfms_alert_active": False,
        "cfms_alert_age_hours": None,
        "top_shap_factors": [
            {"feature_name": "tenure_days", "contribution": -0.15, "direction": "decreases_risk"},
            {"feature_name": "product_complexity", "contribution": -0.05, "direction": "decreases_risk"},
            {"feature_name": "peer_deviation_composite", "contribution": 0.02, "direction": "increases_risk"}
        ],
        "inference_latency_ms": 15.2,
        "model_version": "v1.0.0"
    },
    1001: {
        "account_id": 1001,
        "composite_score": 94.2,
        "risk_tier": "CRITICAL",
        "automated_action": "BLOCK",
        "lgbm_score": 0.824,
        "gnn_mule_score": 0.912,
        "cfms_alert_active": True,
        "cfms_alert_age_hours": 4.5,
        "severity": "HIGH",
        "top_shap_factors": [
            {"feature_name": "peer_deviation_composite", "contribution": 0.312, "direction": "increases_risk"},
            {"feature_name": "F3891", "contribution": 0.194, "direction": "increases_risk"},
            {"feature_name": "F3886", "contribution": 0.145, "direction": "increases_risk"},
            {"feature_name": "tenure_days", "contribution": -0.082, "direction": "decreases_risk"},
            {"feature_name": "product_complexity", "contribution": 0.051, "direction": "increases_risk"}
        ],
        "inference_latency_ms": 28.4,
        "model_version": "v1.0.0"
    },
    2002: {
        "account_id": 2002,
        "composite_score": 76.8,
        "risk_tier": "HIGH",
        "automated_action": "HOLD",
        "lgbm_score": 0.684,
        "gnn_mule_score": 0.732,
        "cfms_alert_active": False,
        "cfms_alert_age_hours": None,
        "top_shap_factors": [
            {"feature_name": "peer_deviation_composite", "contribution": 0.224, "direction": "increases_risk"},
            {"feature_name": "product_complexity", "contribution": 0.182, "direction": "increases_risk"},
            {"feature_name": "tenure_days", "contribution": -0.045, "direction": "decreases_risk"},
            {"feature_name": "F3891", "contribution": 0.088, "direction": "increases_risk"}
        ],
        "inference_latency_ms": 22.1,
        "model_version": "v1.0.0"
    },
    3003: {
        "account_id": 3003,
        "composite_score": 55.4,
        "risk_tier": "MEDIUM",
        "automated_action": "MONITOR",
        "lgbm_score": 0.485,
        "gnn_mule_score": 0.421,
        "cfms_alert_active": True,
        "cfms_alert_age_hours": 120.0,
        "severity": "LOW",
        "top_shap_factors": [
            {"feature_name": "F3886", "contribution": 0.155, "direction": "increases_risk"},
            {"feature_name": "tenure_days", "contribution": -0.112, "direction": "decreases_risk"},
            {"feature_name": "peer_deviation_composite", "contribution": 0.088, "direction": "increases_risk"}
        ],
        "inference_latency_ms": 24.8,
        "model_version": "v1.0.0"
    },
    4004: {
        "account_id": 4004,
        "composite_score": 25.1,
        "risk_tier": "LOW",
        "automated_action": "ALLOW",
        "lgbm_score": 0.210,
        "gnn_mule_score": 0.184,
        "cfms_alert_active": False,
        "cfms_alert_age_hours": None,
        "top_shap_factors": [
            {"feature_name": "tenure_days", "contribution": -0.221, "direction": "decreases_risk"},
            {"feature_name": "product_complexity", "contribution": -0.084, "direction": "decreases_risk"}
        ],
        "inference_latency_ms": 14.5,
        "model_version": "v1.0.0"
    }
}

# Add a default fallback for missing accounts
DEMO_SCORES.setdefault(0, DEMO_SCORES[0])

# Detailed account metadata
DEMO_METADATA = {
    1001: {
        "account_name": "Aditya Sharma",
        "account_type": "Savings",
        "branch": "IIT Hyderabad Ext",
        "risk_status": "Flagged",
        "balance_inr": 482931.22,
        "kyc_status": "Verified",
        "tenure_days": 182,
        "product_complexity": 3,
        "peer_deviation_composite": 4.82
    },
    2002: {
        "account_name": "Priya Patel",
        "account_type": "Current",
        "branch": "Secunderabad Main",
        "risk_status": "Flagged",
        "balance_inr": 1284920.50,
        "kyc_status": "Verified",
        "tenure_days": 745,
        "product_complexity": 8,
        "peer_deviation_composite": 2.11
    },
    3003: {
        "account_name": "Rajesh Kumar",
        "account_type": "MSME Micro",
        "branch": "Gachibowli Tech Park",
        "risk_status": "Flagged",
        "balance_inr": 72491.00,
        "kyc_status": "Pending",
        "tenure_days": 45,
        "product_complexity": 2,
        "peer_deviation_composite": 1.45
    },
    4004: {
        "account_name": "Sunita Rao",
        "account_type": "Savings",
        "branch": "Kondapur Branch",
        "risk_status": "Clear",
        "balance_inr": 95200.40,
        "kyc_status": "Verified",
        "tenure_days": 1420,
        "product_complexity": 1,
        "peer_deviation_composite": 0.22
    }
}

# Main Risk Queue Data
DEMO_QUEUE = [
    {"account_id": 1001, "name": "Aditya Sharma", "type": "Savings", "composite_score": 94.2, "risk_tier": "CRITICAL", "action": "BLOCK", "flagged_reason": "High GNN mule correlation + active high CFMS alert", "last_tx_amount": 150000.0, "time": "2026-06-05 13:45:12"},
    {"account_id": 2002, "name": "Priya Patel", "type": "Current", "composite_score": 76.8, "risk_tier": "HIGH", "action": "HOLD", "flagged_reason": "High peer deviation + rapid out-of-pattern transfers", "last_tx_amount": 500000.0, "time": "2026-06-05 13:42:04"},
    {"account_id": 1002, "name": "Rohan Deshmukh", "type": "Savings", "composite_score": 82.5, "risk_tier": "CRITICAL", "action": "BLOCK", "flagged_reason": "Mule network relay chain hop node", "last_tx_amount": 145000.0, "time": "2026-06-05 13:46:33"},
    {"account_id": 1003, "name": "Vikram Malhotra", "type": "Savings", "composite_score": 89.1, "risk_tier": "CRITICAL", "action": "BLOCK", "flagged_reason": "Mule network relay chain terminal node", "last_tx_amount": 140000.0, "time": "2026-06-05 13:47:50"},
    {"account_id": 3003, "name": "Rajesh Kumar", "type": "MSME Micro", "composite_score": 55.4, "risk_tier": "MEDIUM", "action": "MONITOR", "flagged_reason": "Active CFMS low severity alert + short account tenure", "last_tx_amount": 20000.0, "time": "2026-06-05 13:38:15"},
    {"account_id": 3004, "name": "Ananya Reddy", "type": "Savings", "composite_score": 62.1, "risk_tier": "MEDIUM", "action": "MONITOR", "flagged_reason": "Late-night UPI transaction anomaly", "last_tx_amount": 10000.0, "time": "2026-06-05 02:14:55"},
    {"account_id": 3005, "name": "Siddharth Jain", "type": "Savings", "composite_score": 45.0, "risk_tier": "MEDIUM", "action": "MONITOR", "flagged_reason": "Round amount transfer to new counterparty", "last_tx_amount": 100000.0, "time": "2026-06-05 11:20:44"},
    {"account_id": 4004, "name": "Sunita Rao", "type": "Savings", "composite_score": 25.1, "risk_tier": "LOW", "action": "ALLOW", "flagged_reason": "Low threat score, verified tenure and profile", "last_tx_amount": 1500.0, "time": "2026-06-05 12:00:30"}
]

# Cluster/Network Data for Visualizations
DEMO_CLUSTERS = {
    1001: {
        "root_account_id": 1001,
        "relay_chain_detected": True,
        "cluster_nodes": [
            {"account_id": 1001, "composite_score": 94.2, "gnn_mule_score": 0.912, "risk_tier": "CRITICAL", "automated_action": "BLOCK"},
            {"account_id": 1002, "composite_score": 82.5, "gnn_mule_score": 0.814, "risk_tier": "CRITICAL", "automated_action": "BLOCK"},
            {"account_id": 1003, "composite_score": 89.1, "gnn_mule_score": 0.884, "risk_tier": "CRITICAL", "automated_action": "BLOCK"},
            {"account_id": 1004, "composite_score": 42.8, "gnn_mule_score": 0.380, "risk_tier": "MEDIUM", "automated_action": "MONITOR"},
            {"account_id": 1005, "composite_score": 15.4, "gnn_mule_score": 0.120, "risk_tier": "LOW", "automated_action": "ALLOW"}
        ],
        "cluster_edges": [
            {"source": 1001, "target": 1002, "weight": 0.95, "channel": "UPI", "amount": 150000},
            {"source": 1002, "target": 1003, "weight": 0.92, "channel": "UPI", "amount": 145000},
            {"source": 1001, "target": 1004, "weight": 0.45, "channel": "NEFT", "amount": 50000},
            {"source": 1004, "target": 1005, "weight": 0.20, "channel": "RTGS", "amount": 10000}
        ]
    },
    2002: {
        "root_account_id": 2002,
        "relay_chain_detected": False,
        "cluster_nodes": [
            {"account_id": 2002, "composite_score": 76.8, "gnn_mule_score": 0.732, "risk_tier": "HIGH", "automated_action": "HOLD"},
            {"account_id": 2005, "composite_score": 58.2, "gnn_mule_score": 0.521, "risk_tier": "MEDIUM", "automated_action": "MONITOR"},
            {"account_id": 2006, "composite_score": 22.0, "gnn_mule_score": 0.180, "risk_tier": "LOW", "automated_action": "ALLOW"}
        ],
        "cluster_edges": [
            {"source": 2002, "target": 2005, "weight": 0.70, "channel": "RTGS", "amount": 500000},
            {"source": 2005, "target": 2006, "weight": 0.35, "channel": "NEFT", "amount": 150000}
        ]
    },
    3003: {
        "root_account_id": 3003,
        "relay_chain_detected": False,
        "cluster_nodes": [
            {"account_id": 3003, "composite_score": 55.4, "gnn_mule_score": 0.421, "risk_tier": "MEDIUM", "automated_action": "MONITOR"},
            {"account_id": 3006, "composite_score": 38.5, "gnn_mule_score": 0.290, "risk_tier": "LOW", "automated_action": "ALLOW"}
        ],
        "cluster_edges": [
            {"source": 3003, "target": 3006, "weight": 0.45, "channel": "UPI", "amount": 20000}
        ]
    },
    4004: {
        "root_account_id": 4004,
        "relay_chain_detected": False,
        "cluster_nodes": [
            {"account_id": 4004, "composite_score": 25.1, "gnn_mule_score": 0.184, "risk_tier": "LOW", "automated_action": "ALLOW"}
        ],
        "cluster_edges": []
    }
}
