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
        
        /* Custom style for streamlit tables and dataframes */
        div.stDataFrame {
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
        }
        
        /* Beautiful Scrollbars */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(15, 23, 42, 0.3);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.3);
        }
    </style>
""", unsafe_allow_html=True)

st.title("📋 Risk Queue")
st.caption("Accounts flagged for analyst review — sorted by composite risk score")

st.info("💡 **What is this?** This screen is the alert queue. The AI models run in the background on all transaction streams. When an account violates threat thresholds, it is automatically flagged here so bank analysts can review the risk score, recommended automated action, and alert source.")

with st.expander("📚 Guide: Understanding the Threat Queue Metrics (Click to Expand)", expanded=True):
    st.markdown("""
    - **Account ID**: The unique bank account number flagged. (Commas have been removed from the table below for clean copying/searching).
    - **Composite Risk Score (0-100)**: The unified risk score. A score above **65** is High risk, and above **80** is Critical.
    - **Risk Level**: Classification of threat (Critical, High, Medium, Low).
    - **Recommended Action**: The automated action taken by the gateway:
      - `BLOCK`: Transactions are blocked; account is frozen immediately.
      - `HOLD`: Suspicious transfers are temporarily held for 24 hours.
      - `MONITOR`: Account transactions are logged and observed closely.
      - `ALLOW`: Low-risk normal operation.
    - **Government Alert (CFMS)**: Indicates if the national cybercrime portal (I4C/CFMS) has reported active fraud cases against this account number.
    - **Inference Latency**: The exact time in milliseconds the AI model took to calculate the threat level (typically <90 milliseconds).
    """)

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
    ["CRITICAL", "HIGH", "MEDIUM"], default=["CRITICAL", "HIGH", "MEDIUM"],
    help="Filter accounts by their classified threat severity level.")
cfms_filter = col2.checkbox("Show only CFMS-alerted accounts", value=False,
    help="Check to show only accounts that have an active cybercrime alert in the national registry.")

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
    # Prepare display version of dataframe with friendly column names and formats
    df_display = df.rename(columns={
        "account_id": "Account ID",
        "composite_score": "Composite Risk Score (0-100)",
        "risk_tier": "Risk Level",
        "action": "Recommended Action",
        "cfms": "Government Alert (CFMS)",
        "latency": "Inference Latency"
    })
    
    # Map boolean CFMS to Yes/No icons for clarity
    df_display["Government Alert (CFMS)"] = df_display["Government Alert (CFMS)"].map({True: "🚨 YES", False: "✅ NO"})

    styled = (df_display.style
        .applymap(color_tier, subset=["Risk Level"])
        .applymap(color_action, subset=["Recommended Action"])
        .format({"Account ID": "{}", "Composite Risk Score (0-100)": "{:.1f}", "Inference Latency": "{:.1f}ms"})
    )

    st.dataframe(styled, use_container_width=True, height=350, hide_index=True)

st.divider()

# Quick stats and summary chart using container columns
st.markdown("### 📊 Queue Summary Insights")
col_stats, col_chart = st.columns([1, 2])

with col_stats:
    with st.container(border=True):
        st.markdown("<h5 style='margin-top:0;'>Key Metrics</h5>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if not df.empty:
            c1.metric("CRITICAL Alerts", len(df[df["risk_tier"]=="CRITICAL"]))
            c2.metric("CFMS Reported", len(df[df["cfms"]==True]))
            st.metric("Pending BLOCK Actions", len(df[df["action"]=="BLOCK"]))
        else:
            c1.metric("CRITICAL Alerts", 0)
            c2.metric("CFMS Reported", 0)
            st.metric("Pending BLOCK Actions", 0)

with col_chart:
    with st.container(border=True):
        st.markdown("<h5 style='margin-top:0;'>Alert Severity Distribution</h5>", unsafe_allow_html=True)
        if not df.empty:
            import plotly.graph_objects as go
            tier_counts = df["risk_tier"].value_counts().reset_index()
            tier_counts.columns = ["Risk Level", "Count"]
            
            # Sort in standard order
            order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            tier_counts["sort"] = tier_counts["Risk Level"].map(order)
            tier_counts = tier_counts.sort_values("sort", ascending=False) # low to critical for bottom-up chart
            
            colors_map = {
                "CRITICAL": "#E53935",
                "HIGH":     "#FF9800",
                "MEDIUM":   "#FFD54F",
                "LOW":      "#4CAF50"
            }
            
            fig_summary = go.Figure(go.Bar(
                x=tier_counts["Count"],
                y=tier_counts["Risk Level"],
                orientation="h",
                marker=dict(
                    color=[colors_map.get(t, "#9E9E9E") for t in tier_counts["Risk Level"]],
                    line=dict(color="rgba(255,255,255,0.15)", width=1)
                ),
                text=tier_counts["Count"],
                textposition="outside",
                height=160
            ))
            fig_summary.update_layout(
                margin=dict(l=10, r=30, t=10, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font={"color": "white"},
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", showticklabels=True),
                yaxis=dict(gridcolor="rgba(0,0,0,0)")
            )
            st.plotly_chart(fig_summary, use_container_width=True, config={"displayModeBar": False})
        else:
            st.write("No alerts to summarize.")

st.divider()

# Click to deep dive in a glassmorphic container
st.subheader("🔍 Deep Dive and Triage Investigation")
with st.container(border=True):
    st.write("Select an account from the queue list below to load into the detailed analysis dashboard:")
    
    available_accounts = df["account_id"].tolist() if not df.empty else [1247, 3891, 5042, 7234]
    selected_id = st.selectbox(
        "Choose Account ID to load into Deep Dive",
        options=available_accounts,
        format_func=lambda x: f"Account #{x} (Tier: {df[df['account_id']==x]['risk_tier'].values[0] if not df.empty and x in df['account_id'].values else 'Flagged'})"
    )
    
    if st.button("⚡ Triage & Analyse Account", type="primary"):
        st.session_state["selected_account"] = selected_id
        st.session_state["graph_account"] = selected_id
        st.switch_page("pages/2_Account_Deep_Dive.py")
