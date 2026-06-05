# phase4/dashboard/pages/4_System_Monitor.py
#
# Renders system health and performance monitoring charts: P99 latency SLA targets,
# request throughput rates, and score distribution charts.

import streamlit as st
import plotly.graph_objects as go
import numpy as np

st.title("📊 System Monitor")
st.caption("Real-time performance metrics for FraudGraph Shield")

# Simulated latency time series — replace with real logs in production
np.random.seed(42)
timestamps = [f"08:{i:02d}" for i in range(60)]
latencies  = np.clip(np.random.normal(89, 12, 60), 50, 200).tolist()

fig_latency = go.Figure()
fig_latency.add_trace(go.Scatter(
    x=timestamps, y=latencies,
    mode="lines+markers",
    name="End-to-End Latency (ms)",
    line=dict(color="#2E75B6", width=2),
    marker=dict(size=4)
))
fig_latency.add_hline(y=150, line_dash="dash",
    line_color="red", annotation_text="150ms target")
fig_latency.update_layout(
    title="Inference Latency — Last 60 Minutes",
    yaxis_title="Latency (ms)",
    xaxis_title="Time",
    height=300,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font={"color": "white"},
    xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)")
)
st.plotly_chart(fig_latency, use_container_width=True)

# Score distribution
scores = np.clip(np.random.beta(2, 5, 500) * 100, 0, 100)
fig_dist = go.Figure()
fig_dist.add_trace(go.Histogram(
    x=scores, nbinsx=20,
    marker_color="#2E75B6",
    name="Composite Score Distribution"
))
fig_dist.add_vline(x=40, line_dash="dash", line_color="orange",
    annotation_text="Medium threshold")
fig_dist.add_vline(x=65, line_dash="dash", line_color="red",
    annotation_text="High threshold")
fig_dist.update_layout(
    title="Composite Risk Score Distribution (Last 500 Accounts)",
    xaxis_title="Composite Score",
    yaxis_title="Account Count",
    height=300,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font={"color": "white"},
    xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)")
)
st.plotly_chart(fig_dist, use_container_width=True)

col1, col2, col3, col4 = st.columns(4)
col1.metric("P50 Latency",   "87ms")
col2.metric("P99 Latency",   "143ms")
col3.metric("Requests/hour", "3,240")
col4.metric("Model Version", "v1.0.0")
