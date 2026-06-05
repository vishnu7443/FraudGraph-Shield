# phase4/dashboard/pages/1_Risk_Queue.py
#
# Renders the Risk Queue page, displaying flagged accounts that violate threat thresholds.
# Allows analysts to search, filter by risk severity or recommended action, and select an account for deep-dive.

import streamlit as st
import pandas as pd
import os
import sys

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from demo_data import DEMO_QUEUE
from components.action_badge import get_action_badge, get_risk_tier_badge

st.set_page_config(
    page_title="Risk Queue — FraudGraph Shield",
    page_icon="🛡️",
    layout="wide"
)

# Dark-mode styling for headers & tables
st.markdown("""
    <style>
        .queue-title {
            font-family: 'Outfit', sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 10px;
        }
        .filter-section {
            background: rgba(30, 41, 59, 0.45);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        /* Custom styling for tables */
        div.stDataFrame {
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="queue-title">🛡️ Flagged Risk Queue</div>', unsafe_allow_html=True)
st.markdown("Inspect and triage accounts flagged by the LightGBM, GraphSAGE, and CFMS models.")

# Initialize selected_account_id session state
if "selected_account_id" not in st.session_state:
    st.session_state["selected_account_id"] = 1001

# --- Filter Section ---
st.markdown('<div class="filter-section">', unsafe_allow_html=True)
col_filter_tier, col_filter_action, col_search = st.columns([1, 1, 2])

with col_filter_tier:
    tier_filter = st.selectbox(
        "Risk Tier",
        options=["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
    )

with col_filter_action:
    action_filter = st.selectbox(
        "Automated Action",
        options=["All", "ALLOW", "MONITOR", "HOLD", "BLOCK"]
    )

with col_search:
    search_query = st.text_input("🔍 Search by Account ID or Customer Name", "")
st.markdown('</div>', unsafe_allow_html=True)

# Convert DEMO_QUEUE to DataFrame
df_queue = pd.DataFrame(DEMO_QUEUE)

# Apply filters
if tier_filter != "All":
    df_queue = df_queue[df_queue["risk_tier"] == tier_filter]
    
if action_filter != "All":
    df_queue = df_queue[df_queue["action"] == action_filter]
    
if search_query:
    search_query = search_query.strip().lower()
    df_queue = df_queue[
        df_queue["account_id"].astype(str).str.contains(search_query) | 
        df_queue["name"].str.lower().str.contains(search_query)
    ]

# Display queue metrics
col_total, col_crit, col_hold = st.columns(3)
with col_total:
    st.metric("Total Filtered Alerts", len(df_queue))
with col_crit:
    st.metric("Critical Blocks Required", len(df_queue[df_queue["action"] == "BLOCK"]))
with col_hold:
    st.metric("TMS Holds Pending", len(df_queue[df_queue["action"] == "HOLD"]))

st.markdown("---")

# Render custom HTML table or interactable dataframe
if df_queue.empty:
    st.warning("No flagged alerts match the selected criteria.")
else:
    # Prepare display dataframe
    df_display = df_queue.copy()
    
    # Render interactive grid using st.dataframe
    # Custom format configurations
    st.dataframe(
        df_display[[
            "account_id", "name", "type", "composite_score", 
            "risk_tier", "action", "last_tx_amount", "time", "flagged_reason"
        ]].rename(columns={
            "account_id": "Account ID",
            "name": "Customer Name",
            "type": "Account Type",
            "composite_score": "Composite Score",
            "risk_tier": "Risk Tier",
            "action": "Action",
            "last_tx_amount": "Last Transfer (₹)",
            "time": "Detection Time",
            "flagged_reason": "Risk Description Flag"
        }),
        column_config={
            "Composite Score": st.column_config.NumberColumn(format="%.1f"),
            "Last Transfer (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
        },
        use_container_width=True,
        hide_index=True
    )

    # Selection Panel for Deep Dive
    st.markdown("### 🔍 Investigate & Score Account")
    col_select, col_btn = st.columns([2, 1])
    
    with col_select:
        # Populate selectbox with filtered list
        acc_options = df_queue["account_id"].tolist()
        default_index = acc_options.index(st.session_state["selected_account_id"]) if st.session_state["selected_account_id"] in acc_options else 0
        
        selected_id = st.selectbox(
            "Select Account ID to load into Deep Dive",
            options=acc_options,
            index=default_index,
            format_func=lambda x: f"Acc {x} — {df_queue[df_queue['account_id']==x]['name'].values[0]} ({df_queue[df_queue['account_id']==x]['risk_tier'].values[0]})"
        )
        st.session_state["selected_account_id"] = selected_id
        
    with col_btn:
        st.write("") # padding
        st.write("") # padding
        st.info("💡 Once selected, navigate to the '**2_Account_Deep_Dive**' page in the sidebar.")
