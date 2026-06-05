# phase4/dashboard/pages/1_Risk_Queue.py
#
# Renders the Risk Queue page displaying flagged alerts.
# Supports live batch scoring watchlists or pre-baked fallback datasets with color-coded rows.

import streamlit as st
import pandas as pd
import os
import sys

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from demo_data import DEMO_RISK_QUEUE
from api_client import score_batch

st.set_page_config(
    page_title="Risk Queue — FraudGraph Shield",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Risk Queue")
st.caption("Accounts flagged for analyst review — sorted by composite risk score")

use_demo = st.session_state.get("use_demo", True)

if use_demo:
    queue_data = DEMO_RISK_QUEUE
else:
    # In live mode, batch score a set of watch-list accounts
    watch_list = [{"account_id": i, "transaction_amount": 50000,
                   "channel": "UPI", "hour_of_day": 14}
                  for i in range(50)]
    results = score_batch(watch_list) or []
    queue_data = [
        {"account_id": r["account_id"],
         "composite_score": r["composite_score"],
         "risk_tier": r["risk_tier"],
         "action": r["automated_action"],
         "cfms": r["cfms_alert_active"],
         "latency": r["inference_latency_ms"]}
        for r in results if r["risk_tier"] != "LOW"
    ]

# If queue_data is empty, fallback to demo data to keep the screen active
if not queue_data:
    queue_data = DEMO_RISK_QUEUE

# Filter controls
col1, col2 = st.columns(2)
tier_filter = col1.multiselect("Filter by Risk Tier",
    ["CRITICAL", "HIGH", "MEDIUM"], default=["CRITICAL", "HIGH", "MEDIUM"])
cfms_filter = col2.checkbox("Show only CFMS-alerted accounts", value=False)

df = pd.DataFrame(queue_data)
if tier_filter:
    df = df[df["risk_tier"].isin(tier_filter)]
if cfms_filter:
    df = df[df["cfms"] == True]

# Color-code rows by risk tier
def color_tier(val):
    colors = {
        "CRITICAL": "background-color: #581c1c; color: #fca5a5; font-weight: bold",
        "HIGH":     "background-color: #5c3b1e; color: #fed7aa; font-weight: bold",
        "MEDIUM":   "background-color: #1e3a8a; color: #bfdbfe",
        "LOW":      "background-color: #064e3b; color: #a7f3d0"
    }
    return colors.get(val, "")

def color_action(val):
    colors = {
        "BLOCK":   "background-color: #ef4444; color: white; font-weight: bold",
        "HOLD":    "background-color: #f97316; color: white",
        "MONITOR": "background-color: #3b82f6; color: white",
        "ALLOW":   "background-color: #10b981; color: white"
    }
    return colors.get(val, "")

# Format dataframe nicely
if df.empty:
    st.warning("No flagged alerts match the selected criteria.")
else:
    styled = (df.style
        .applymap(color_tier, subset=["risk_tier"])
        .applymap(color_action, subset=["action"])
        .format({"composite_score": "{:.1f}", "latency": "{:.1f}ms"})
    )

    st.dataframe(styled, use_container_width=True, height=350)

st.divider()

# Quick stats
c1, c2, c3 = st.columns(3)
if not df.empty:
    c1.metric("CRITICAL accounts", len(df[df["risk_tier"]=="CRITICAL"]))
    c2.metric("CFMS-alerted", len(df[df["cfms"]==True]))
    c3.metric("Pending BLOCK action", len(df[df["action"]=="BLOCK"]))
else:
    c1.metric("CRITICAL accounts", 0)
    c2.metric("CFMS-alerted", 0)
    c3.metric("Pending BLOCK action", 0)

# Click to deep dive
st.subheader("Deep Dive into an Account")
selected_id = st.number_input("Enter Account ID", min_value=0,
                               max_value=9081, value=1247, step=1)
if st.button("🔍 Analyse Account", type="primary"):
    st.session_state["selected_account"] = selected_id
    st.switch_page("pages/2_Account_Deep_Dive.py")
