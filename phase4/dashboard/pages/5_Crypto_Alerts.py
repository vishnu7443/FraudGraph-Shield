# phase4/dashboard/pages/5_Crypto_Alerts.py
#
# Renders the Cryptocurrency Exit Detection alerts panel, featuring KPI metrics,
# dynamic alerts list, and interactive Plotly distributions.

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api_client import get_crypto_alerts, require_login

st.set_page_config(
    page_title="Crypto Exits — FraudGraph Shield",
    page_icon="🪙",
    layout="wide"
)

# Enforce JWT analyst login
require_login()

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
            font-size: 28px !important;
            font-weight: 800 !important;
            color: #ffffff !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        }
        div[data-testid="stMetricLabel"] {
            font-family: 'Inter', sans-serif !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            color: rgba(255, 255, 255, 0.6) !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🪙 Cryptocurrency Exit Detection alerts")
st.caption("Monitoring transaction routing to registered Virtual Digital Asset (VDA) exchanges and P2P gateways")
st.divider()

# Fetch Alerts Data
alerts_data = get_crypto_alerts()

if not alerts_data:
    st.info("No cryptocurrency exit alerts detected.")
    st.stop()

# Convert to DataFrame
df = pd.DataFrame(alerts_data)

# KPI Metrics Cards Row
col1, col2, col3, col4 = st.columns(4)

total_alerts = len(df)
total_value = df["amount"].sum()
hold_orders = len(df[df["status"] == "OPEN"])
unique_exchanges = df["exchange"].nunique()

with col1:
    st.metric("Crypto Alerts", f"{total_alerts}", "+0 new")
with col2:
    st.metric("Total Value Held", f"₹{total_value:,.2f}", "INR Lock")
with col3:
    st.metric("Active HOLD Orders", f"{hold_orders}", "Regulatory Action")
with col4:
    st.metric("VDA Gateways Flagged", f"{unique_exchanges}", "Exchanges")

st.divider()

# Alerts Queue Table
with st.container(border=True):
    st.subheader("📋 Crypto Exit Alerts Queue")
    
    # Format columns for display
    display_df = df.copy()
    display_df["amount"] = display_df["amount"].map(lambda x: f"₹{x:,.2f}")
    display_df["risk_score"] = display_df["risk_score"].map(lambda x: f"{x:.1f}")
    display_df["account_id"] = display_df["account_id"].astype(str)
    
    # Reorder columns
    display_df = display_df[[
        "alert_id", "txn_id", "account_id", "exchange", 
        "amount", "risk_score", "severity", "hold_reason", "timestamp", "status"
    ]]
    
    # Display table without index column
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.divider()

# Charts Grid
col_left, col_right = st.columns([1, 1])

with col_left:
    with st.container(border=True):
        st.subheader("📊 Exchange Distribution")
        fig_pie = px.pie(
            df, 
            names="exchange", 
            values="amount",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Oranges_r
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    with st.container(border=True):
        st.subheader("📈 Risk Score Distribution")
        fig_hist = px.histogram(
            df, 
            x="risk_score",
            nbins=10,
            color_discrete_sequence=["#FF9800"],
            labels={"risk_score": "Composite Score"}
        )
        fig_hist.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
        )
        st.plotly_chart(fig_hist, use_container_width=True)

with st.container(border=True):
    st.subheader("📅 Alerts Daily Timeline")
    # Group by date
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    trend_df = df.groupby("date").size().reset_index(name="Alert Count")
    
    fig_line = px.line(
        trend_df,
        x="date",
        y="Alert Count",
        markers=True,
        color_discrete_sequence=["#E53935"]
    )
    fig_line.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", dtick=1)
    )
    st.plotly_chart(fig_line, use_container_width=True)
