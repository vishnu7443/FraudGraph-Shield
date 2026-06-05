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

# Dropdown selector to switch accounts directly on the deep-dive page
available_accounts = [1247, 3891, 5042, 7234]
current_selected = st.session_state.get("selected_account", 1247)
if current_selected not in available_accounts:
    available_accounts.append(current_selected)

selected_account = st.selectbox(
    "🔎 Select Account to Investigate",
    options=available_accounts,
    index=available_accounts.index(current_selected),
    help="Select which flagged bank account to investigate. This updates the SHAP explanation, gauges, and network graphs."
)

# Update session state if changed
if selected_account != current_selected:
    st.session_state["selected_account"] = selected_account
    # Clear the last simulated result so we load the default profile of the new account
    if "last_result" in st.session_state:
        del st.session_state["last_result"]
    st.rerun()

account_id = selected_account
use_demo = st.session_state.get("use_demo", True)

# Scoring controls
st.subheader(f"Simulate Transaction for Account #{account_id}")
col1, col2, col3, col4 = st.columns(4)
amount   = col1.number_input("Transaction Amount (₹)", value=50000, step=1000,
                             help="The monetary value of the incoming/outgoing transfer in Indian Rupees (INR). Spikes in amounts trigger transaction model alerts.")
channel  = col2.selectbox("Channel", ["UPI", "NEFT", "RTGS", "ATM", "MOBILE"],
                          help="The channel used for the transfer. High-velocity UPI transfers are typical in automated fraud, while RTGS/NEFT are for larger amounts.")
hour     = col3.slider("Hour of Day", 0, 23, 14,
                       help="The hour at which the transfer was initiated. Midnight transfers (11 PM - 4 AM) are flagged as high risk.")
new_cp   = col4.checkbox("New Counterparty",
                         help="Check if the destination account has never transacted with the sender before. New connections have higher risk weighting.")

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
col1.metric("Composite Score", f"{result['composite_score']:.1f}/100", 
            help="Unified Threat Rating: A weighted fusion combining transaction parameters (35%), network graph connections (40%), and government alerts (25%).")
col2.metric("LightGBM Score",  f"{result['lgbm_score']:.3f}",
            help="Transaction pattern anomaly risk (calculated from amount value, payments channel type, late-night hours, and new counterparty flags).")
col3.metric("GNN Mule Score",  f"{result['gnn_mule_score']:.3f}",
            help="Network connection risk: checks whether this node belongs to a dense subgraph connected to known mule accounts using Graph Neural Networks.")
col4.metric("Latency",         f"{result['inference_latency_ms']:.1f}ms",
            help="Scoring latency of the pipeline. Must remain below the bank's 350ms speed limit.")
cfms_text = "🚨 YES" if result["cfms_alert_active"] else "✅ NO"
col5.metric("CFMS Alert", cfms_text,
            help="Checks whether this account has an active case filed in the national I4C / FIU-IND cybercrime registries.")

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

st.info("💡 **How to interpret these risk dimensions (for non-technical presenters):**\n"
        "- **Composite Risk Score (0-100)**: The final rating. A weighted blend of: **35% Transaction Model**, **40% Graph Neural Network**, and **25% Government Alert**. Scores above **80** automatically trigger a `BLOCK`.\n"
        "- **LightGBM Score (0 to 1)**: Evaluates *current activity*. Flags irregular amounts, late-night transfers, or sending money to brand new recipients.\n"
        "- **GNN Mule Score (0 to 1)**: Evaluates *network behavior*. Using a Graph Neural Network, it maps transaction relationships across the bank. If this account is closely linked (1-2 hops away) to known mule accounts, its GNN score rises close to `1.0`.\n"
        "- **CFMS Alert**: Yes/No flag showing if this account ID has a cybercrime report filed in the national cybercrime portal.")

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

st.caption("🔍 **How to read the SHAP chart:** Red bars represent features that pushed the score higher (increased risk, e.g., peer activity deviation), while Green bars represent features that dragged the score lower (decreased risk, e.g., long account age/tenure).")

st.divider()
if st.button("🕸️ View Account Network Graph →", type="secondary"):
    st.session_state["graph_account"] = account_id
    st.switch_page("pages/3_Network_Graph.py")
