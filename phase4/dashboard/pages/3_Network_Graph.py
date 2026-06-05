# phase4/dashboard/pages/3_Network_Graph.py
#
# Renders the GraphSAGE network visualization page. Traces transaction connections
# and identifies co-suspicious mule account networks and temporal fund routing relay chains.

import streamlit as st
import streamlit.components.v1 as components
import os
import sys

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api_client import get_cluster
from demo_data import DEMO_METADATA
from components.network_viz import generate_network_html
from components.action_badge import get_risk_tier_badge

st.set_page_config(
    page_title="Mule Network Visualization — FraudGraph Shield",
    page_icon="🛡️",
    layout="wide"
)

# Page styles
st.markdown("""
    <style>
        .net-title {
            font-family: 'Outfit', sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 15px;
        }
        .net-card {
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .alert-banner {
            background: rgba(220, 38, 38, 0.15);
            border: 1.5px solid #ef4444;
            border-radius: 8px;
            padding: 15px;
            color: #fca5a5;
            font-size: 14px;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="net-title">🕸️ GraphSAGE Mule Network Visualization</div>', unsafe_allow_html=True)
st.markdown("Inspect transaction hops, counterparty networks, and suspicious money relay chains mapped by the GraphSAGE GNN.")

# Load active target account
selected_acc_id = st.session_state.get("selected_account_id", 1001)

# Selector in sidebar
st.sidebar.markdown("### 🕸️ Select Graph Root")
acc_choices = list(DEMO_METADATA.keys())
sidebar_acc = st.sidebar.selectbox(
    "Root Account ID",
    options=acc_choices,
    index=acc_choices.index(selected_acc_id) if selected_acc_id in acc_choices else 0
)

# Update state if changed
if sidebar_acc != selected_acc_id:
    st.session_state["selected_account_id"] = sidebar_acc
    selected_acc_id = sidebar_acc
    st.rerun()

# Retrieve cluster representation from api client
with st.spinner("Retrieving GraphSAGE cluster nodes & edges..."):
    cluster_data = get_cluster(selected_acc_id)

if not cluster_data:
    st.error("Failed to load network cluster data.")
else:
    # Check if a relay chain is flagged
    relay_detected = cluster_data.get("relay_chain_detected", False)
    
    if relay_detected:
        st.markdown(f"""
            <div class="alert-banner">
                🚨 <b>CRITICAL MULE RELAY CHAIN FLAGGED:</b> Account <b>{selected_acc_id}</b> is routing funds in a consecutive temporal chain 
                (1001 &rarr; 1002 &rarr; 1003) within a 5-minute interval. This indicates automated syndicate laundering. 
                Recommended Action: <b>Block Core Banking System (CBS) transfers on all nodes in this chain immediately.</b>
            </div>
        """, unsafe_allow_html=True)
        
    # Render Graph layout: 3/4 network, 1/4 node details list
    col_viz, col_nodes = st.columns([3, 1])
    
    with col_viz:
        st.markdown("**Interactive Network Visualization (Pan, Zoom, Hover for details)**")
        
        # Call component to build HTML code
        nodes = cluster_data.get("cluster_nodes", [])
        edges = cluster_data.get("cluster_edges", [])
        
        html_code = generate_network_html(nodes, edges, selected_acc_id)
        
        # Render the PyVis generated html frame
        components.html(html_code, height=480)
        
        # Key Legend
        st.markdown("""
        <div style="font-size: 12px; color: #94a3b8; display: flex; gap: 20px; justify-content: center; margin-top: 10px;">
            <span><span style="color: #dc2626; font-size: 14px;">●</span> Critical Risk</span>
            <span><span style="color: #f97316; font-size: 14px;">●</span> High Risk</span>
            <span><span style="color: #f59e0b; font-size: 14px;">●</span> Medium Risk</span>
            <span><span style="color: #3b82f6; font-size: 14px;">●</span> Low Risk</span>
            <span><b>Channels:</b> <span style="color: #22d3ee;">Cyan = UPI</span> | <span style="color: #a855f7;">Purple = RTGS</span> | <span style="color: #34d399;">Green = NEFT</span></span>
        </div>
        """, unsafe_allow_html=True)
        
    with col_nodes:
        st.markdown("**Cluster Accounts Details**")
        st.markdown(f"Total Nodes: `{len(nodes)}` | Total Connections: `{len(edges)}`")
        
        # List nodes
        for node in nodes:
            node_id = node["account_id"]
            tier = node["risk_tier"]
            score = node["composite_score"]
            action = node["automated_action"]
            
            # Format text color & details
            is_root_str = " (Root Target)" if node_id == selected_acc_id else ""
            
            st.markdown(f"""
            <div class="net-card" style="padding: 10px; margin-bottom: 10px; font-size: 12px;">
                <b>Account ID:</b> `{node_id}` {is_root_str}<br/>
                <b>Risk Score:</b> <b>{score:.1f}</b><br/>
                <b>Tier:</b> {get_risk_tier_badge(tier)}<br/>
                <b>Action:</b> <code>{action}</code>
            </div>
            """, unsafe_allow_html=True)

    # Relay path explanation
    if relay_detected:
        st.markdown("### 🔍 Traced Fund Hopping Pattern")
        st.markdown("""
        The network demonstrates a high-velocity, round-number flow. Syndicate operators split high amounts into 
        mule nodes to evade single transaction alerts:
        1. **Node 1001 (Aditya Sharma)** receives an outside payment of ₹150,000 via UPI.
        2. **Node 1002 (Rohan Deshmukh)** receives ₹145,000 via UPI within 90 seconds.
        3. **Node 1003 (Vikram Malhotra)** receives ₹140,000 via UPI within 3 minutes of Node 1002.
        
        This behavior matches a **Layering Phase** mule chain designed to quickly siphon cash before bank risk managers can block the account.
        """)
