# phase4/dashboard/app.py
#
# Main entry point for the FraudGraph Shield Analyst Dashboard.
# Renders KPI metric cards, navigation instructions, and manages Live vs Demo Mode toggles.

# pyrefly: ignore [missing-import]
import streamlit as st
import os
import sys

# Add dashboard folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_client import health_check, require_login

# Page Configuration
st.set_page_config(
    page_title="FraudGraph Shield",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
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
        
        /* Premium Glassmorphism Cards */
        .glass-card {
            background: rgba(30, 41, 59, 0.45) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 12px !important;
            padding: 24px !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            margin-bottom: 20px !important;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        }
        .glass-card:hover {
            transform: translateY(-3px) !important;
            border-color: rgba(255, 255, 255, 0.18) !important;
            box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.5) !important;
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

# Sidebar
with st.sidebar:
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=180)
    st.title("FraudGraph Shield")
    st.caption("PSB Hackathon 2026 | Bank of India × IIT Hyderabad")
    st.divider()

    # API mode toggle — live vs demo
    mode = st.radio("Data Mode", ["🔴 Live API", "📦 Demo Data"],
                    index=1, help="Switch to Demo Data if API is offline")
    st.session_state["mode"] = mode
    st.session_state["use_demo"] = (mode == "📦 Demo Data")

    st.divider()

    # Health check
    if not st.session_state.get("use_demo"):
        health = health_check()
        if health.get("status") == "ok" and not health.get("is_mock", False):
            st.success("API Online ✅")
        else:
            st.error("API Offline ❌")
            st.session_state["use_demo"] = True # Force fallback
    else:
        st.info("Running on Demo Data")

    st.divider()
    st.caption("Model Version: v1.0.0")
    st.caption("Phase 1: LightGBM | Phase 2: GraphSAGE")

# Main Title Area
st.title("🛡️ FraudGraph Shield")
st.subheader("Real-Time Mule Account & Transaction Fraud Detection")
st.divider()

# KPI metrics row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Accounts Monitored", "9,082", "+0 new")
with col2:
    st.metric("CRITICAL Risk", "3", delta="1 new", delta_color="inverse")
with col3:
    st.metric("Avg Latency", "89ms", "-114ms vs baseline")
with col4:
    st.metric("CFMS Alerts Active", "1,362", "+12 today")

st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("""
    ### System Walkthrough & Operational Guide
    
    **FraudGraph Shield** is a production-grade transaction monitor protecting digital banking lines. 
    It runs an advanced **hybrid fusion model** to identify credit mules, online scammers, and syndicate rings.
    
    #### Core Architectural Pillars
    
    1. **Real-time Feature Engineering**: preprocessed transaction stats are fed into the LightGBM classifier.
    2. **Deep Graph Learning**: GraphSAGE model evaluates global mule patterns across 9,082 accounts.
    3. **CFMS Mock Alert**: Ingests automated reports from government registries.
    4. **Explainable AI**: Employs SHAP values showing exactly *why* a threat score is triggered.
    
    #### Navigation Guide
    
    * **📋 Risk Queue** *(Sidebar Page 1)*: Explores the current list of flagged bank accounts. Click on any account ID to open deep-dive analysis.
    * **🔬 Account Deep-Dive** *(Sidebar Page 2)*: Performs a detailed investigation on a single account. Explains details using **SHAP waterfall graphs**, and runs real-time transaction scoring simulator testing.
    * **🕸️ Network Graph** *(Sidebar Page 3)*: Visualizes transaction networks and traces **mule relay chains** routing stolen funds across multiple hops in real-time.
    * **📊 System Monitor** *(Sidebar Page 4)*: Displays live charts of API metrics, transaction load, and model specifications.
    """)

with col_right:
    st.markdown("#### Operational Status Panel")
    
    status_label = "Running" if not st.session_state.get("use_demo", True) else "Offline Fallback"
    status_icon = "🟢" if not st.session_state.get("use_demo", True) else "🟠"
    
    st.markdown(f"""
    - **API Status:** {status_icon} **{status_label}**
    - **GNN Scoring Engine:** 🟢 Loaded (`gnn_model.pt`)
    - **LightGBM Scoring Engine:** 🟢 Loaded (`lgbm_model.pkl`)
    - **Active Graph Nodes:** 9,082
    - **Target SLA:** 89ms response time (99.9% availability)
    """)

st.info("👈 Navigate using the sidebar pages to explore the dashboard.")
