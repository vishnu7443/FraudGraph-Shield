# phase4/dashboard/pages/2_Account_Deep_Dive.py
#
# Renders the individual account deep-dive, including score gauges, SHAP waterfall impact charts,
# feature store metrics, and an interactive transaction simulator.

import streamlit as st
import pandas as pd
import numpy as np
import os
import sys

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api_client import score_transaction
from demo_data import DEMO_METADATA, DEMO_SCORES
from components.score_gauge import render_score_gauge
from components.action_badge import get_action_badge, get_risk_tier_badge
from components.shap_chart import render_shap_chart

st.set_page_config(
    page_title="Account Deep Dive — FraudGraph Shield",
    page_icon="🛡️",
    layout="wide"
)

# Typography & Glassmorphism card styles
st.markdown("""
    <style>
        .deep-title {
            font-family: 'Outfit', sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 15px;
        }
        .section-header {
            font-family: 'Outfit', sans-serif;
            font-size: 18px;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 12px;
            border-left: 3px solid #3b82f6;
            padding-left: 8px;
        }
        .deep-card {
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .badge-row {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# Select default account from session state or query params
selected_acc_id = st.session_state.get("selected_account_id", 1001)

st.markdown('<div class="deep-title">🔍 Account Risk Deep-Dive</div>', unsafe_allow_html=True)

# Sidebar selector to change target account quickly
st.sidebar.markdown("### 🎯 Investigation Target")
acc_choices = list(DEMO_METADATA.keys())
sidebar_acc = st.sidebar.selectbox(
    "Active Account ID",
    options=acc_choices,
    index=acc_choices.index(selected_acc_id) if selected_acc_id in acc_choices else 0
)

# Update state if changed
if sidebar_acc != selected_acc_id:
    st.session_state["selected_account_id"] = sidebar_acc
    selected_acc_id = sidebar_acc
    st.rerun()

# Fetch metadata
meta = DEMO_METADATA.get(selected_acc_id, {
    "account_name": f"Unknown Acc {selected_acc_id}",
    "account_type": "Savings",
    "branch": "Unknown Branch",
    "risk_status": "Flagged",
    "balance_inr": 0.0,
    "kyc_status": "Unknown",
    "tenure_days": 1,
    "product_complexity": 1,
    "peer_deviation_composite": 0.0
})

# Display Customer Profile Header Card
st.markdown('<div class="deep-card">', unsafe_allow_html=True)
col_prof1, col_prof2, col_prof3, col_prof4 = st.columns(4)
with col_prof1:
    st.markdown(f"**Customer Name:** {meta['account_name']}")
    st.markdown(f"**Account ID:** `{selected_acc_id}`")
with col_prof2:
    st.markdown(f"**Account Type:** {meta['account_type']}")
    st.markdown(f"**Branch Location:** {meta['branch']}")
with col_prof3:
    st.markdown(f"**Balance (INR):** ₹{meta['balance_inr']:,.2f}")
    st.markdown(f"**KYC Verification:** `{meta['kyc_status']}`")
with col_prof4:
    st.markdown(f"**Account Age:** {meta['tenure_days']} days")
    st.markdown(f"**Peer Activity Deviation:** `{meta['peer_deviation_composite']:.2f}x`")
st.markdown('</div>', unsafe_allow_html=True)

# Get current/pre-calculated scores for account
pre_score = DEMO_SCORES.get(selected_acc_id, DEMO_SCORES[0])

# Layout: Gauge on left, SHAP waterfall explanation on right
col_gauge, col_shap = st.columns([1, 1])

with col_gauge:
    st.markdown('<div class="section-header">Composite Risk Assessment</div>', unsafe_allow_html=True)
    st.markdown('<div class="deep-card" style="text-align: center;">', unsafe_allow_html=True)
    
    # Render Plotly gauge
    score_val = pre_score["composite_score"]
    fig_gauge = render_score_gauge(score_val)
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    # Badges Row
    badge_html = f"""
    <div class="badge-row" style="justify-content: center;">
        <span>Risk Tier: {get_risk_tier_badge(pre_score['risk_tier'])}</span>
        <span>Decision: {get_action_badge(pre_score['automated_action'])}</span>
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)
    
    # Model Splits
    st.markdown(f"""
    <div style="font-size: 13px; color: #94a3b8; text-align: left; padding: 10px 20px;">
        • <b>LightGBM Transaction Score:</b> {pre_score.get('lgbm_score', 0.0):.4f}<br/>
        • <b>GraphSAGE GNN Mule Score:</b> {pre_score.get('gnn_mule_score', 0.0):.4f}<br/>
        • <b>CFMS Active Alert:</b> {"Yes" if pre_score.get('cfms_alert_active') else "No"}<br/>
        • <b>Inference Latency:</b> {pre_score.get('inference_latency_ms', 0.0):.2f} ms
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col_shap:
    st.markdown('<div class="section-header">Explainable AI (SHAP Waterfall)</div>', unsafe_allow_html=True)
    st.markdown('<div class="deep-card">', unsafe_allow_html=True)
    st.write("Visualizes the feature contributions increasing (red) or decreasing (green) the risk score.")
    
    # Render SHAP Chart
    fig_shap = render_shap_chart(pre_score.get("top_shap_factors", []))
    st.plotly_chart(fig_shap, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Real-Time Transaction Simulator ---
st.markdown('<div class="section-header">⚡ Live Real-Time Transaction Simulator</div>', unsafe_allow_html=True)
st.markdown("""
    Test transaction parameters in real-time. This queries the **Risk Fusion Engine API** (or falls back to demo matrices if offline) 
    using the active feature-store cached variables for this account ID.
""")

st.markdown('<div class="deep-card">', unsafe_allow_html=True)
col_sim1, col_sim2, col_sim3 = st.columns(3)

with col_sim1:
    sim_amount = st.number_input("Transaction Amount (INR)", min_value=1.0, value=25000.0, step=1000.0)
    sim_channel = st.selectbox("Payment Channel", options=["UPI", "NEFT", "RTGS", "ATM", "MOBILE"])
    
with col_sim2:
    sim_hour = st.slider("Hour of Day (0-23)", min_value=0, max_value=23, value=14)
    sim_round_amount = st.checkbox("Is Round Amount (e.g. ₹50000)", value=False)

with col_sim3:
    sim_new_counterparty = st.checkbox("Is New Counterparty", value=False)
    st.write("") # Spacer
    st.write("") # Spacer
    run_score = st.button("⚡ Execute Score Engine", type="primary")

if run_score:
    with st.spinner("Scoring transaction with pipeline..."):
        score_res = score_transaction(
            account_id=selected_acc_id,
            amount=sim_amount,
            channel=sim_channel,
            hour=sim_hour,
            is_new_counterparty=sim_new_counterparty,
            is_round_amount=sim_round_amount
        )
        
        if score_res:
            st.session_state[f"sim_res_{selected_acc_id}"] = score_res
            st.success("Scoring complete! Visualizations above have updated.")
            
            # Show simulated details
            st.markdown("#### Simulation Pipeline Log Output")
            col_log1, col_log2 = st.columns(2)
            with col_log1:
                st.json(score_res)
            with col_log2:
                # Explain the boosters applied
                boosters = []
                if sim_round_amount: boosters.append("+3.0 (Round Amount Anomaly)")
                if sim_new_counterparty: boosters.append("+2.0 (New Counterparty Risk)")
                if sim_hour in [0,1,2,3,4]: boosters.append("+4.0 (Late-Night Transfer)")
                if sim_channel == "UPI" and score_res.get("lgbm_score", 0) > 0.6: boosters.append("+3.0 (High Risk UPI Booster)")
                
                st.markdown("**Boosters Applied:**")
                if boosters:
                    for b in boosters:
                        st.markdown(f"- `{b}`")
                else:
                    st.markdown("- *None*")
                    
                # Update visual display state dynamically
                DEMO_SCORES[selected_acc_id] = score_res
                st.rerun()
        else:
            st.error("Failed to score transaction.")
st.markdown('</div>', unsafe_allow_html=True)
