# phase4/dashboard/pages/2_Account_Deep_Dive.py
#
# Renders the individual account deep-dive, including score gauges, SHAP waterfall charts,
# and an interactive transaction simulator.

import streamlit as st
import plotly.graph_objects as go
import os
import sys

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api_client import score_transaction
from demo_data import DEMO_SCORES

st.title("🔬 Account Deep Dive")

account_id = st.session_state.get("selected_account", 1247)
use_demo = st.session_state.get("use_demo", True)

# Custom fonts
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap');
        h1, h2, h3, h4, .stHeader {
            font-family: 'Outfit', sans-serif !important;
            font-weight: 700 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Scoring controls
st.subheader(f"Account #{account_id}")
col1, col2, col3, col4 = st.columns(4)
amount   = col1.number_input("Transaction Amount (₹)", value=50000, step=1000)
channel  = col2.selectbox("Channel", ["UPI", "NEFT", "RTGS", "ATM", "MOBILE"])
hour     = col3.slider("Hour of Day", 0, 23, 14)
new_cp   = col4.checkbox("New Counterparty")

if st.button("⚡ Score Transaction", type="primary"):
    with st.spinner("Scoring..."):
        if use_demo:
            result = DEMO_SCORES.get(str(account_id), DEMO_SCORES.get(account_id, list(DEMO_SCORES.values())[0]))
        else:
            result = score_transaction(account_id, amount, channel, hour, new_cp)

    if result:
        st.session_state["last_result"] = result

result = st.session_state.get("last_result",
         DEMO_SCORES.get(str(account_id), DEMO_SCORES.get(account_id, list(DEMO_SCORES.values())[0])))

st.divider()

# Score display row
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Composite Score", f"{result['composite_score']:.1f}/100")
col2.metric("LightGBM Score",  f"{result['lgbm_score']:.3f}")
col3.metric("GNN Mule Score",  f"{result['gnn_mule_score']:.3f}")
col4.metric("Latency",         f"{result['inference_latency_ms']:.1f}ms")
cfms_text = "🚨 YES" if result["cfms_alert_active"] else "✅ NO"
col5.metric("CFMS Alert", cfms_text)

# Risk tier badge
tier_colors = {
    "CRITICAL": "#C00000", "HIGH": "#B45F06",
    "MEDIUM": "#1967D2",   "LOW": "#2E7D32"
}
action_labels = {
    "BLOCK": "🔴 BLOCK", "HOLD": "🟡 HOLD",
    "MONITOR": "🔵 MONITOR", "ALLOW": "🟢 ALLOW"
}
tier  = result["risk_tier"]
color = tier_colors.get(tier, "#404040")
st.markdown(
    f'<div style="background:{color};color:white;padding:12px 24px;'
    f'border-radius:8px;font-size:20px;font-weight:bold;text-align:center;margin:12px 0">'
    f'Risk Tier: {tier} — {action_labels[result["automated_action"]]}</div>',
    unsafe_allow_html=True
)

st.divider()

# Composite score gauge
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=result["composite_score"],
    title={"text": "Composite Risk Score"},
    gauge={
        "axis": {"range": [0, 100]},
        "bar": {"color": color},
        "steps": [
            {"range": [0, 40],  "color": "rgba(46, 125, 50, 0.1)"},
            {"range": [40, 65], "color": "rgba(25, 103, 210, 0.1)"},
            {"range": [65, 80], "color": "rgba(180, 95, 6, 0.1)"},
            {"range": [80, 100],"color": "rgba(192, 0, 0, 0.1)"},
        ],
        "threshold": {
            "line": {"color": "red", "width": 4},
            "thickness": 0.75,
            "value": result["composite_score"]
        }
    }
))
fig_gauge.update_layout(height=280, margin=dict(t=40, b=0, l=20, r=20), paper_bgcolor='rgba(0,0,0,0)', font={"color": "white"})
st.plotly_chart(fig_gauge, use_container_width=True)

st.divider()

# SHAP waterfall chart
st.subheader("🧠 Why was this account flagged? (SHAP Explanation)")
shap_factors = result["top_shap_factors"]
feature_names = [f["feature_name"].replace("_", " ").title() for f in shap_factors]
contributions = [f["contribution"] for f in shap_factors]
colors_shap   = ["#C00000" if c > 0 else "#2E7D32" for c in contributions]

fig_shap = go.Figure(go.Bar(
    y=feature_names,
    x=contributions,
    orientation="h",
    marker_color=colors_shap,
    text=[f"+{c:.4f}" if c > 0 else f"{c:.4f}" for c in contributions],
    textposition="outside"
))
fig_shap.update_layout(
    title="Top 5 Risk Factors (SHAP Contribution)",
    xaxis_title="SHAP Value (impact on risk score)",
    height=350,
    margin=dict(l=20, r=20, t=50, b=20),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor='rgba(0,0,0,0)',
    font={"color": "white"},
    xaxis=dict(zeroline=True, zerolinecolor="white", zerolinewidth=1, gridcolor="rgba(255,255,255,0.1)"),
    yaxis=dict(gridcolor="rgba(0,0,0,0)")
)
st.plotly_chart(fig_shap, use_container_width=True)

st.caption("Red bars increase fraud risk. Green bars decrease fraud risk.")

st.divider()
if st.button("🕸️ View Account Network Graph →", type="secondary"):
    st.session_state["graph_account"] = account_id
    st.switch_page("pages/3_Network_Graph.py")
