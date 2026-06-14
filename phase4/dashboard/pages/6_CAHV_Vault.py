# phase4/dashboard/pages/6_CAHV_Vault.py
#
# Renders the Cloud Account Holder Vault (CAHV) analyst page.
# Supports secure customer lookup using hashed identifier, decryption display,
# Plotly scatter timelines, and manual data simulation.

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys
import hashlib
import time

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api_client import get_vault_profile, create_vault_alert, get_vault_alerts

st.set_page_config(
    page_title="CAHV Vault — FraudGraph Shield",
    page_icon="🔒",
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
        
        .profile-container {
            background: rgba(15, 23, 42, 0.4) !important;
            border-radius: 10px;
            padding: 20px;
            border-left: 5px solid #2563EB;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🔒 Cloud Account Holder Vault (CAHV)")
st.caption("Secure centralized PII identity retrieval utilizing SHA-256 account hashes and AES-256-GCM encryption")
st.divider()

# Sidebar: Helper Utilities and Simulation Forms
with st.sidebar:
    st.subheader("🛠️ Investigator Utility Panel")
    st.divider()
    
    # 1. Hashing converter utility
    st.markdown("### 🔢 Account ID Hasher")
    raw_acc_input = st.text_input("Raw Account ID", value="1247", help="Input bank account number to compute its SHA-256 query hash")
    if raw_acc_input:
        computed_hash = hashlib.sha256(raw_acc_input.strip().encode('utf-8')).hexdigest()
        st.code(computed_hash, language="text")
        st.caption("Double-click code to copy hash for lookup")
        
    st.divider()
    
    # 2. Simulator Actions Selector
    st.markdown("### ⚙️ Vault Simulator")
    sim_action = st.selectbox("Choose Simulation", ["Lookup Search", "Register New Profile", "Submit Fraud Alert"])

# Main Flow Controller
if sim_action == "Lookup Search":
    st.subheader("🔍 Investigator Account Search")
    
    # Main Search Input
    search_hash = st.text_input(
        "Enter SHA-256 Account Hash / Hashed ID", 
        value=hashlib.sha256(b"1247").hexdigest(), 
        placeholder="e.g. f94d2a4c..."
    ).strip()
    
    if search_hash:
        with st.spinner("Decrypting vault records..."):
            case_data = get_vault_profile(search_hash)
            
        if not case_data or "profile" not in case_data:
            st.error("No account record matching this hash found in the secure vault.")
        else:
            profile = case_data["profile"]
            summary = case_data["summary"]
            
            # Fetch alerts including dynamically added mock alerts if running in offline mode
            alerts_data = get_vault_alerts(search_hash)
            
            # Recalculate metrics on the fly if dynamic alerts were added
            if alerts_data:
                total_alerts = len(alerts_data)
                highest_risk = max(a["risk_score"] for a in alerts_data)
                last_alert = alerts_data[0]["created_at"]
            else:
                total_alerts = summary.get("total_alerts", 0)
                highest_risk = summary.get("highest_risk", 0.0)
                last_alert = summary.get("last_alert", "NEVER")
            
            # Split Layout: Left for Demographics, Right for Case Summary KPIs
            col_left, col_right = st.columns([1, 1])
            
            with col_left:
                st.markdown("### 👤 Decrypted Demographics")
                # Premium profile details card
                st.markdown(f"""
                <div class="profile-container">
                    <p style='margin:0; font-size:12px; font-weight:600; color:#3B82F6;'>SECURE ENCRYPTED ACCOUNT DATA</p>
                    <h3 style='margin: 5px 0 15px 0; color:#FFFFFF;'>{profile.get("name", "Unknown")}</h3>
                    <table style='width:100%; border-collapse:collapse; color:#E2E8F0;'>
                        <tr>
                            <td style='padding: 5px 0; font-weight:600; width:30%;'>Hashed ID:</td>
                            <td style='padding: 5px 0; font-family:monospace; font-size:11px; word-break:break-all;'>{profile.get("hashed_id", "N/A")}</td>
                        </tr>
                        <tr>
                            <td style='padding: 5px 0; font-weight:600;'>Account Number:</td>
                            <td>{profile.get("account_id", "N/A")} (Vault Decrypted)</td>
                        </tr>
                        <tr>
                            <td style='padding: 5px 0; font-weight:600;'>Mobile Phone:</td>
                            <td>{profile.get("phone", "N/A")}</td>
                        </tr>
                        <tr>
                            <td style='padding: 5px 0; font-weight:600;'>PAN Card:</td>
                            <td style='font-family:monospace;'>{profile.get("pan", "N/A")}</td>
                        </tr>
                        <tr>
                            <td style='padding: 5px 0; font-weight:600;'>Email Address:</td>
                            <td>{profile.get("email", "N/A")}</td>
                        </tr>
                        <tr>
                            <td style='padding: 5px 0; font-weight:600;'>Registered At:</td>
                            <td>{profile.get("created_at", "N/A")}</td>
                        </tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
                
            with col_right:
                st.markdown("### 📊 Case Risk Summary")
                # KPI metrics
                m_col1, m_col2, m_col3 = st.columns(3)
                with m_col1:
                    st.metric("Total Alerts Logged", f"{total_alerts}")
                with m_col2:
                    st.metric("Highest Risk Score", f"{highest_risk:.1f}", delta=None)
                with m_col3:
                    # Clean date for display
                    display_date = last_alert.split("T")[0] if "T" in last_alert else last_alert
                    st.metric("Last Alert Date", display_date)
                    
                st.divider()
                st.info("⚠️ Accessing this profile registers a secure investigator query to the audit trail log file.")
                
            st.divider()
            
            # Alerts Timeline and Alerts Table
            st.markdown("### 📈 Risk Timeline & Severity Tracker")
            if not alerts_data:
                st.info("No threat alerts have been logged for this account holder.")
            else:
                # Plotly Timeline scatter chart
                df = pd.DataFrame(alerts_data)
                df["datetime"] = pd.to_datetime(df["created_at"])
                df = df.sort_values(by="datetime")
                
                fig = px.scatter(
                    df,
                    x="datetime",
                    y="risk_score",
                    color="category",
                    size="risk_score",
                    hover_name="alert_type",
                    hover_data={
                        "alert_id": True,
                        "source": True,
                        "notes": True,
                        "risk_score": ":.1f",
                        "datetime": "|%B %d, %Y %H:%M"
                    },
                    color_discrete_map={
                        "Transaction Risk": "#EF4444",
                        "Identity Risk": "#3B82F6",
                        "Network Risk": "#F59E0B",
                        "Crypto Risk": "#10B981"
                    },
                    labels={"datetime": "Event Date", "risk_score": "Composite Score"},
                    range_y=[0, 110]
                )
                
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="white",
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)"),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Alerts Logs Table
                with st.container(border=True):
                    st.subheader("📋 Threat Log Ledger")
                    display_df = df.copy().sort_values(by="datetime", ascending=False)
                    display_df = display_df[[
                        "alert_id", "risk_score", "alert_type", "category", "source", "notes", "created_at"
                    ]]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)

elif sim_action == "Register New Profile":
    st.subheader("📝 Register New Secure Customer Profile")
    st.markdown("Simulate the encryption of raw identity values into the database vault.")
    
    with st.form("register_form"):
        account_id = st.number_input("Account Node ID (Integer)", min_value=1000, max_value=999999, value=5042)
        name = st.text_input("Full Name", value="Rajesh Kumar")
        phone = st.text_input("Phone Number", value="+91 99887 76655")
        pan = st.text_input("PAN Number", value="CRDKP4912J")
        email = st.text_input("Email Address", value="rajesh.kumar@bankofindia.co.in")
        
        submitted = st.form_submit_button("Encrypt & Register Profile")
        
        if submitted:
            # We call our backend API client to register the profile
            import httpx
            from api_client import API_BASE
            
            payload = {
                "account_id": int(account_id),
                "name": name,
                "phone": phone,
                "pan": pan,
                "email": email
            }
            
            with st.spinner("Performing AES-256 encryption..."):
                try:
                    # Check if running offline
                    if st.session_state.get("use_demo"):
                        mock_hash = hashlib.sha256(str(account_id).strip().encode('utf-8')).hexdigest()
                        st.success("Demo Mode: Profile encrypted and hashed successfully!")
                        st.markdown(f"**Generated SHA-256 Lookup Key:** `{mock_hash}`")
                        st.info("You can now search for this hash to retrieve your record.")
                    else:
                        resp = httpx.post(f"{API_BASE}/vault/account", json=payload, timeout=5.0)
                        if resp.status_code == 200:
                            data = resp.json()
                            st.success("Success! Customer profile registered securely.")
                            st.markdown(f"**Generated SHA-256 Lookup Key:** `{data['hashed_id']}`")
                            st.info("Copy this hash to perform lookups.")
                        else:
                            st.error(f"Backend registration failed: {resp.text}")
                except Exception as e:
                    st.error(f"Could not connect to API backend to register: {str(e)}")

elif sim_action == "Submit Fraud Alert":
    st.subheader("🚨 Report / Register Fraud Threat Alert")
    st.markdown("Trigger a secure alert entry tied to a specific customer's account hash.")
    
    with st.form("alert_form"):
        hashed_id = st.text_input(
            "Target Hashed ID (Account Hash)", 
            value=hashlib.sha256(b"1247").hexdigest(),
            help="Hashed lookup key of the customer"
        )
        risk_score = st.slider("Risk Score (0-100)", min_value=0, max_value=100, value=85)
        alert_type = st.selectbox("Alert Code / Type", ["MULE_ACCOUNT", "CRYPTO_EXIT", "ACCOUNT_TAKEOVER", "SUSPICIOUS_PAYEE", "IDENTITY_THEFT"])
        category = st.selectbox("Risk Category", ["Transaction Risk", "Identity Risk", "Network Risk", "Crypto Risk"])
        source = st.selectbox("Reporting Source", ["Manual Investigator", "Crypto Detector", "Fusion Engine", "External Registry"])
        notes = st.text_area("Investigator Notes", value="Account flagged during manual transaction velocity review.")
        
        submitted = st.form_submit_button("Submit Alert to Vault")
        
        if submitted:
            with st.spinner("Submitting threat report to CAHV..."):
                res = create_vault_alert(
                    hashed_id=hashed_id.strip(),
                    risk_score=float(risk_score),
                    alert_type=alert_type,
                    category=category,
                    source=source,
                    notes=notes
                )
                if res and res.get("success"):
                    st.success(f"Threat alert registered! Generated Alert Reference: `{res.get('alert_id')}`")
                    st.info("Look up this hashed ID again to see the updated metrics and timeline.")
                else:
                    st.error("Failed to register alert. Please check backend connection.")
