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

from api_client import get_vault_profile, create_vault_alert, get_vault_alerts, require_login, get_audit_logs, verify_audit_chain, simulate_audit_tampering

st.set_page_config(
    page_title="CAHV Vault — FraudGraph Shield",
    page_icon="🔒",
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
    
    # Simulator Actions Selector
    st.markdown("### ⚙️ Vault Simulator")
    role = st.session_state.get("role", "analyst")
    if role == "admin":
        sim_options = ["Lookup Search", "Register New Profile", "Submit Fraud Alert", "Cryptographic Audit Ledger"]
    else:
        sim_options = ["Lookup Search", "Submit Fraud Alert"]
    
    sim_action = st.selectbox("Choose Simulation", sim_options)

# Main Flow Controller
if sim_action == "Lookup Search":
    st.subheader("🔍 Investigator Account Search")
    
    # Main Search Input
    search_acc_num = st.text_input(
        "Enter Account Number", 
        value="1247", 
        placeholder="e.g. 1247"
    ).strip()
    
    if search_acc_num:
        search_hash = hashlib.sha256(search_acc_num.encode('utf-8')).hexdigest()
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
                            <td style='padding: 5px 0; font-weight:600; width:30%;'>Account Number:</td>
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
    
    if st.session_state.get("role") != "admin":
        st.error("🚫 Access Denied: Only users with the 'admin' role are permitted to register new customer profiles in the vault.")
    else:
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
                            st.info(f"You can now search for account number '{account_id}' to retrieve your record.")
                        else:
                            headers = {}
                            if "jwt_token" in st.session_state and st.session_state["jwt_token"]:
                                headers["Authorization"] = f"Bearer {st.session_state['jwt_token']}"
                            resp = httpx.post(f"{API_BASE}/vault/account", json=payload, headers=headers, timeout=5.0)
                            if resp.status_code == 200:
                                data = resp.json()
                                st.success("Success! Customer profile registered securely.")
                                st.info(f"You can now search for account number '{account_id}' to perform lookups.")
                            elif resp.status_code == 403:
                                st.error("🚫 Operation Forbidden: Insufficient role permissions.")
                            else:
                                st.error(f"Backend registration failed: {resp.text}")
                    except Exception as e:
                        st.error(f"Could not connect to API backend to register: {str(e)}")

elif sim_action == "Submit Fraud Alert":
    st.subheader("🚨 Report / Register Fraud Threat Alert")
    st.markdown("Trigger a secure alert entry tied to a specific customer's account hash.")
    
    with st.form("alert_form"):
        target_acc_num = st.text_input(
            "Target Account Number", 
            value="1247",
            help="Account number of the customer"
        )
        risk_score = st.slider("Risk Score (0-100)", min_value=0, max_value=100, value=85)
        alert_type = st.selectbox("Alert Code / Type", ["MULE_ACCOUNT", "CRYPTO_EXIT", "ACCOUNT_TAKEOVER", "SUSPICIOUS_PAYEE", "IDENTITY_THEFT"])
        category = st.selectbox("Risk Category", ["Transaction Risk", "Identity Risk", "Network Risk", "Crypto Risk"])
        source = st.selectbox("Reporting Source", ["Manual Investigator", "Crypto Detector", "Fusion Engine", "External Registry"])
        notes = st.text_area("Investigator Notes", value="Account flagged during manual transaction velocity review.")
        
        submitted = st.form_submit_button("Submit Alert to Vault")
        
        if submitted:
            hashed_id = hashlib.sha256(target_acc_num.strip().encode('utf-8')).hexdigest()
            with st.spinner("Submitting threat report to CAHV..."):
                res = create_vault_alert(
                    hashed_id=hashed_id,
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

elif sim_action == "Cryptographic Audit Ledger":
    st.subheader("🛡️ Cryptographic Hash-Chained Audit Trail")
    st.markdown("Inspect and verify the blockchain-like audit trail tracking access history, lookup logs, and registered alerts.")

    # 1. Fetch ledger
    logs = get_audit_logs()
    
    # 2. Main actions: Verify Chain & Tamper Simulator
    col_verify, col_tamper = st.columns([1.5, 1])
    
    with col_verify:
        st.markdown("### 🔍 Security Verification")
        if st.button("⚡ Verify Chain Integrity", type="primary", use_container_width=True):
            with st.spinner("Executing SHA-256 cryptographic sequence check..."):
                res = verify_audit_chain()
                if res.get("verified", False):
                    st.success(f"🟢 **INTEGRITY VERIFIED**: {res.get('message', 'All links successfully matched.')}")
                    st.toast("Verification Complete: Integrity Verified ✅")
                else:
                    st.error(f"🚨 **TAMPER DETECTED**: Chain verification failed at block index #{res.get('tampered_index')}!")
                    st.markdown(f"**Reason**: `{res.get('reason')}`")
                    st.markdown(f"**Expected Hash**: `{res.get('expected')}`")
                    st.markdown(f"**Found/Stored Hash**: `{res.get('found')}`")
                    st.json(res.get("record", {}))
                    st.toast("Tampering Detected! ❌", icon="⚠️")
                    
    with col_tamper:
        st.markdown("### ⚙️ Demo Tamper Simulator")
        st.write("Simulate an unauthorized attack by modifying past database entries to test if the hashing checks identify it:")
        if logs:
            log_indices = [l["log_index"] for l in logs]
            target_index = st.selectbox("Select Log Index to Tamper", options=log_indices)
            if st.button("🔴 Inject Malicious Edit", use_container_width=True):
                with st.spinner("Altering past log record..."):
                    res = simulate_audit_tampering(target_index)
                    if res.get("success"):
                        st.warning(f"⚠️ **Tampering Successful!** Record #{target_index} modified. Click 'Verify Chain Integrity' to run the verification engine.")
                        time.sleep(1.0)
                        st.rerun()
                    else:
                        st.error("Failed to alter record.")
        else:
            st.info("No audit logs registered to simulate tampering.")

    st.divider()
    
    # 3. Render ledger list
    if logs:
        st.markdown("### 📋 Cryptographic Log Ledger")
        df_logs = pd.DataFrame(logs)
        df_display = df_logs.copy()
        
        # Display nicely
        st.dataframe(
            df_display[[
                "log_index", "timestamp", "action", "username", "role", "endpoint", "hashed_id", "previous_hash", "current_hash"
            ]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No audit log records are currently registered.")
