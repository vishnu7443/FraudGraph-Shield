# phase4/dashboard/pages/4_System_Monitor.py
#
# Renders system health and performance monitoring charts: P99 latency SLA targets,
# request throughput rates, and score distribution charts.

import streamlit as st
import plotly.graph_objects as go
import numpy as np

st.set_page_config(
    page_title="System Monitor — FraudGraph Shield",
    page_icon="📊",
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

st.title("📊 System Monitor")
st.caption("Real-time performance metrics and scoring SLA health check")

# Simulated latency time series — replace with real logs in production
np.random.seed(42)
timestamps = [f"08:{i:02d}" for i in range(60)]
latencies  = np.clip(np.random.normal(89, 12, 60), 50, 200).tolist()

with st.container(border=True):
    st.subheader("⏱️ Inference Latency SLA Tracking")
    fig_latency = go.Figure()
    fig_latency.add_trace(go.Scatter(
        x=timestamps, y=latencies,
        mode="lines+markers",
        name="End-to-End Latency (ms)",
        line=dict(color="#3b82f6", width=2),
        marker=dict(size=5, color="#22d3ee")
    ))
    fig_latency.add_hline(y=150, line_dash="dash",
        line_color="#ef4444", annotation_text="150ms P99 Target Limit", annotation_position="top left")
    fig_latency.update_layout(
        title="Scoring Latency — Last 60 Minutes",
        yaxis_title="Latency (ms)",
        xaxis_title="Time",
        height=280,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)")
    )
    st.plotly_chart(fig_latency, use_container_width=True)

st.divider()

# Score distribution
scores = np.clip(np.random.beta(2, 5, 500) * 100, 0, 100)

with st.container(border=True):
    st.subheader("📈 Risk Classification Profiling")
    fig_dist = go.Figure()
    fig_dist.add_trace(go.Histogram(
        x=scores, nbinsx=25,
        marker=dict(color="rgba(59, 130, 246, 0.75)", line=dict(color="#3b82f6", width=1)),
        name="Composite Score Distribution"
    ))
    fig_dist.add_vline(x=40, line_dash="dash", line_color="#f59e0b",
        annotation_text="Medium Threshold", annotation_position="top left")
    fig_dist.add_vline(x=65, line_dash="dash", line_color="#f97316",
        annotation_text="High Threshold", annotation_position="top left")
    fig_dist.add_vline(x=80, line_dash="dash", line_color="#ef4444",
        annotation_text="Critical Action", annotation_position="top left")
    fig_dist.update_layout(
        title="Composite Risk Score Distribution (Last 500 Analyzed Accounts)",
        xaxis_title="Composite Score Value",
        yaxis_title="Account Counts",
        height=280,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)")
    )
    st.plotly_chart(fig_dist, use_container_width=True)

st.divider()

# SLA stats container card
with st.container(border=True):
    st.subheader("⚙️ System Performance Statistics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("P50 Latency",   "87ms", "-2ms vs baseline")
    col2.metric("P99 Latency",   "143ms", "-11ms vs SLA target")
    col3.metric("Throughput Rate", "3,240 req/hr", "+4% spike")
    col4.metric("Model Version", "v1.0.0", "Active Deployment")
