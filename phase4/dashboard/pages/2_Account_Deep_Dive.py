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
from components.score_gauge import render_score_gauge
from components.shap_chart import render_shap_chart

st.set_page_config(
    page_title="Account Deep Dive — FraudGraph Shield",
    page_icon="🔬",
    layout="wide"
)

# Custom Global CSS for Dark Mode Glassmorphism
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap');
        
        /* Global Font & Color Palette Overrides */
        html, body, [class*="css"], .stMarkdown {
            font-family: 'Inter', sans-serif !important;
        }
        h1, h2, h3, h4, .stHeader {
            font-family: 'Outfit', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: -0.5px;
        }
        
        /* Slate Dark Background Accent */
        .stApp {
            background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 100%) !important;
        }
        
        /* Target Streamlit's native bordered containers to look like glass cards */
        div[data-testid="stVerticalBlockBorder"] {
            background: rgba(30, 41, 59, 0.45) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 12px !important;
            padding: 20px !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
        }
        
        /* Metric Card Styling */
        div[data-testid="stMetricValue"] {
            font-family: 'Outfit', sans-serif !important;
            font-size: 30px !important;
            font-weight: 800 !important;
            color: #ffffff !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        }
        div[data-testid="stMetricLabel"] {
            font-family: 'Inter', sans-serif !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            color: rgba(255, 255, 255, 0.6) !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🔬 Account Deep Dive")
st.caption("Granular forensic analysis, AI factor explanations (SHAP), and transaction simulator")

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
    st.session_state["graph_account"] = selected_account
    # Clear the last simulated result so we load the default profile of the new account
    if "last_result" in st.session_state:
        del st.session_state["last_result"]
    st.rerun()

account_id = selected_account
use_demo = st.session_state.get("use_demo", True)

# Scoring controls inside bordered glass card
with st.container(border=True):
    st.subheader(f"⚡ Live Transaction Simulator (Account #{account_id})")
    st.write("Modify the parameters below to test how the AI composite score reacts in real time:")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    amount   = col1.number_input("Transaction Amount (₹)", value=50000, step=1000,
                                 help="The monetary value of the incoming/outgoing transfer in Indian Rupees (INR). Spikes in amounts trigger transaction model alerts.")
    channel  = col2.selectbox("Channel", ["UPI", "NEFT", "RTGS", "ATM", "MOBILE"],
                              help="The channel used for the transfer. High-velocity UPI transfers are typical in automated fraud, while RTGS/NEFT are for larger amounts.")
    hour     = col3.slider("Hour of Day", 0, 23, 14,
                           help="The hour at which the transfer was initiated. Midnight transfers (11 PM - 4 AM) are flagged as high risk.")
    dest_name = col4.text_input("Destination / Payee", value="",
                                help="Payee name or destination account owner. Enter WazirX or CoinDCX to test high-risk crypto exit detection.")
    new_cp   = col5.checkbox("New Counterparty",
                             help="Check if the destination account has never transacted with the sender before. New connections have higher risk weighting.")

    if st.button("⚡ Score Transaction", type="primary"):
        with st.spinner("Scoring..."):
            result = score_transaction(account_id, amount, channel, hour, new_cp, destination_name=dest_name)

        if result:
            st.session_state["last_result"] = result

result = st.session_state.get("last_result",
         DEMO_SCORES.get(str(account_id), DEMO_SCORES.get(account_id, list(DEMO_SCORES.values())[0])))

st.divider()

# Score display row inside a container card
with st.container(border=True):
    st.subheader("📊 Threat Assessment Dashboard")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
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
    
    crypto_detected = result.get("crypto_detected", False)
    crypto_text = f"🚨 {result.get('crypto_exchange')}" if crypto_detected else "✅ CLEAR"
    col6.metric("Crypto Exit", crypto_text,
                help="Checks whether the transaction destination matches any high-risk virtual digital asset (VDA) exchange aliases.")


# Risk tier status bar
tier_colors = {
    "CRITICAL": "#E53935", "HIGH": "#FF9800",
    "MEDIUM": "#1967D2",   "LOW": "#2E7D32"
}
action_labels = {
    "BLOCK": "🔴 BLOCK (Immediate transaction freeze)", 
    "HOLD": "🟡 HOLD (Lock funds for verification)",
    "MONITOR": "🔵 MONITOR (Observe future transactions)", 
    "ALLOW": "🟢 ALLOW (Proceed normally)"
}
tier  = result["risk_tier"]
color = tier_colors.get(tier, "#404040")
st.markdown(
    f'<div style="background:{color};color:white;padding:14px 24px;'
    f'border-radius:10px;font-size:20px;font-weight:bold;text-align:center;margin:16px 0;'
    f'box-shadow: 0 4px 15px {color}44;">'
    f'Risk Tier: {tier} — Recommended Action: {action_labels[result["automated_action"]]}</div>',
    unsafe_allow_html=True
)

st.info("💡 **How to interpret these risk dimensions (for non-technical presenters):**\n"
        "- **Composite Risk Score (0-100)**: The final rating. A weighted blend of: **35% Transaction Model (LGBM)**, **40% Graph Neural Network (GNN)**, and **25% Government Alert (CFMS)**. Scores above **80** automatically trigger a `BLOCK`.\n"
        "- **LightGBM Score (0 to 1)**: Evaluates *current transaction activity*. Flags irregular amounts, late-night transfers, or sending money to brand new recipients.\n"
        "- **GNN Mule Score (0 to 1)**: Evaluates *network connection behavior*. Using a Graph Neural Network, it maps transaction relationships across the bank. If this account is closely linked (1-2 hops away) to known mule accounts, its GNN score rises close to `1.0`.\n"
        "- **CFMS Alert**: Yes/No case alert showing if this account ID has a cybercrime report filed in the national registry portal.")

st.divider()

# Visual indicators: radial gauge and SHAP waterfall chart side-by-side
col_gauge, col_shap = st.columns([1, 1.2])

with col_gauge:
    with st.container(border=True):
        st.markdown("<h4 style='margin-top:0;'>Composite Threat Rating</h4>", unsafe_allow_html=True)
        fig_gauge = render_score_gauge(result["composite_score"])
        st.plotly_chart(fig_gauge, use_container_width=True)

with col_shap:
    with st.container(border=True):
        st.markdown("<h4 style='margin-top:0;'>Primary Risk Factors (SHAP Explanation)</h4>", unsafe_allow_html=True)
        fig_shap = render_shap_chart(result["top_shap_factors"])
        st.plotly_chart(fig_shap, use_container_width=True)
        st.caption("🔍 **How to read the SHAP chart:** Red bars represent features that pushed the score higher (increased risk), while Green bars represent features that dragged the score lower (decreased risk).")

st.divider()
if st.button("🕸️ View Account Network Graph →", type="secondary"):
    st.session_state["graph_account"] = account_id
    st.switch_page("pages/3_Network_Graph.py")
