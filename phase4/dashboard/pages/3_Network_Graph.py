# phase4/dashboard/pages/3_Network_Graph.py
#
# Renders the GraphSAGE network visualization page. Uses PyVis to draw interactive graph
# structures colored by GNN mule scores, highlighting co-suspicious transaction pathways.

import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network
from api_client import get_cluster
from demo_data import DEMO_CLUSTERS
import tempfile
import os
import sys

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

st.title("🕸️ Mule Account Network Graph")
st.caption("Interactive relay chain visualization — powered by Graph Neural Networks (GraphSAGE)")

# Imports needed for root score lookup
from demo_data import DEMO_SCORES, DEMO_CLUSTERS

# Account Selector
available_accounts = [1247, 3891, 5042, 7234]
current_selected = st.session_state.get("graph_account", 1247)
if current_selected not in available_accounts:
    available_accounts.append(current_selected)

selected_account = st.selectbox(
    "🔎 Select Account to Visualize Network",
    options=available_accounts,
    index=available_accounts.index(current_selected),
    help="Select which bank account's transaction network to visualize. Try Account 1247 to witness the money relay chain."
)

if selected_account != current_selected:
    st.session_state["graph_account"] = selected_account
    st.rerun()

account_id = selected_account
use_demo   = st.session_state.get("use_demo", True)
hop_depth  = st.slider("Hop depth", 1, 3, 2,
    help="How many transaction hops to traverse from the root account")

if use_demo:
    cluster = DEMO_CLUSTERS.get(str(account_id), DEMO_CLUSTERS.get(account_id, list(DEMO_CLUSTERS.values())[0]))
else:
    cluster = get_cluster(account_id, hop_depth)

if not cluster:
    st.warning("No cluster data available.")
    st.stop()

# PyVis network setup with 50 iterations for an active, float-in physics animation
net = Network(
    height="600px", width="100%",
    bgcolor="#0F1117",         # dark background
    font_color="white",
    directed=True
)
net.set_options("""
{
  "physics": {
    "enabled": true,
    "stabilization": {"iterations": 50}
  },
  "edges": {
    "arrows": {"to": {"enabled": true, "scaleFactor": 1.2}},
    "color": {"color": "#555555"},
    "width": 1.5
  }
}
""")

def score_to_color(score: float) -> str:
    if score >= 0.8:    return "#E53935"   # Vibrant Red — critical mule probability
    elif score >= 0.65: return "#FF9800"   # Orange — high risk
    elif score >= 0.4:  return "#FFD54F"   # Yellow/Amber — medium risk
    else:               return "#4CAF50"   # Green — low risk normal account

def score_to_size(score: float) -> int:
    return int(20 + score * 40)          # bigger node = higher GNN risk weight

root_id = cluster["root_account_id"]
nodes   = cluster["cluster_nodes"]

# Determine root node score dynamically to color it correctly
if use_demo:
    root_score_data = DEMO_SCORES.get(str(root_id), DEMO_SCORES.get(root_id, {}))
else:
    from api_client import score_transaction
    root_score_data = score_transaction(root_id, 50000, "UPI", 14) or {}

root_mule_score = root_score_data.get("gnn_mule_score", root_score_data.get("composite_score", 0.0))
root_norm_score = root_mule_score / 100.0 if root_mule_score > 1.0 else root_mule_score
root_color = score_to_color(root_norm_score)
root_size = score_to_size(root_norm_score)

# Add root node explicitly if not present in the GNN nodes list to prevent AssertionError
has_root = any(node["account_id"] == root_id for node in nodes)
if not has_root:
    net.add_node(
        root_id,
        label=f"Acc #{root_id}\n(Root)",
        color={"background": root_color, "border": "#FFFFFF"},
        size=root_size,
        title=f"Root Target Node Account: {root_id}\nRisk Score: {root_norm_score:.4f}",
        borderWidth=3
    )

# Add neighbor nodes
for node in nodes:
    acc_id   = node["account_id"]
    # Handle schema variance: some nodes use mule_score, others use composite_score
    score    = node.get("mule_score", node.get("composite_score", 0.0))
    # Standardize score scaling (if 0-100 scale, normalize to 0-1)
    norm_score = score / 100.0 if score > 1.0 else score
    
    color    = score_to_color(norm_score)
    size     = score_to_size(norm_score)
    label    = f"Acc #{acc_id}\n{norm_score:.2f}"
    border   = "#FFFFFF" if acc_id == root_id else color
    title    = (f"Account: {acc_id}\n"
                f"Mule Score: {norm_score:.4f}\n"
                f"Type: {node.get('account_type', 'Unknown')}\n"
                f"Risk: {node.get('risk_tier', 'LOW')}")

    net.add_node(
        acc_id,
        label=label,
        color={"background": color, "border": border},
        size=size,
        title=title,
        borderWidth=3 if acc_id == root_id else 1
    )

# Add default relation edges (grey arrows representing transaction routing)
for i, node in enumerate(nodes):
    target_id = node["account_id"]
    if target_id != root_id:
        m_score = node.get("mule_score", node.get("composite_score", 0.0))
        norm_m_score = m_score / 100.0 if m_score > 1.0 else m_score
        
        net.add_edge(root_id, target_id,
                     title=f"Transaction Link",
                     width=max(1.5, int(norm_m_score * 4)))

# Draw sequential orange dashed edges connecting the high-risk nodes (>= 0.8 score)
# to highlight the "money relay chain" traversing them.
high_risk_nodes = [n for n in nodes if n.get("mule_score", n.get("composite_score", 0.0)) >= 0.8]
if high_risk_nodes:
    first_high_risk_id = high_risk_nodes[0]["account_id"]
    if first_high_risk_id != root_id:
        net.add_edge(
            root_id,
            first_high_risk_id,
            color="#FF6B00",
            width=3.5,
            dashes=True,
            title="Money Relay Entry Point"
        )
        
    for i in range(len(high_risk_nodes) - 1):
        source_id = high_risk_nodes[i]["account_id"]
        target_id = high_risk_nodes[i+1]["account_id"]
        if source_id != target_id:
            net.add_edge(
                source_id,
                target_id,
                color="#FF6B00",
                width=3.5,
                dashes=True,
                title="Suspected Money Relay Hop"
            )

# Render to temp HTML
temp_dir = tempfile.gettempdir()
temp_file_path = os.path.join(temp_dir, f"pyvis_graph_{account_id}.html")

net.save_graph(temp_file_path)
with open(temp_file_path, "r", encoding="utf-8") as f:
    html = f.read()
os.unlink(temp_file_path)

# Custom css override to remove default margins
style_override = """
<style>
    body { margin: 0; padding: 0; background-color: #0F1117; overflow: hidden; }
</style>
"""
html = html.replace("<style>", style_override + "<style>")

# Show cluster stats
relay = cluster.get("relay_chain_detected", False)
# Handle schema variance for cluster_risk_score
cluster_risk = cluster.get("cluster_risk_score", max([n.get("mule_score", n.get("composite_score", 0.0)) for n in nodes]) if nodes else 0.0)
norm_cluster_risk = cluster_risk / 100.0 if cluster_risk > 1.0 else cluster_risk

col1, col2, col3 = st.columns(3)
col1.metric("Accounts in Cluster", len(nodes), 
            help="Total number of bank accounts connected via direct transaction links in this network neighborhood.")
col2.metric("Cluster Risk Score",  f"{norm_cluster_risk:.3f}",
            help="The maximum GNN mule correlation score observed in this neighborhood. A higher score means a denser threat cluster.")
col3.metric("Relay Chain", "🚨 DETECTED" if relay else "✅ None",
            help="Identifies high-velocity, round-number consecutive transfers siphoned through multiple hops (layering).")

st.info("💡 **Presenter Guideline (IIT Hyderabad Hackathon Winning Moment):**\n"
        "1. Click on **Account 1247** to display the GNN transaction neighborhood.\n"
        "2. Point out the **Vibrant Red Nodes** (Critical Mule Accounts) and the **Thick Orange Dashed Arrows**.\n"
        "3. Explain to the judges: **'This is the money relay chain, frozen in real time. We are tracing the cash flow from the victim's account through a sequence of mule layers before it can be siphoned out.'**")

if relay:
    st.error("⚠️ Money relay chain detected. Recommend immediate freeze of all cluster accounts.")

st.divider()
components.html(html, height=620, scrolling=False)
st.caption("Visual Legend: Node Size = risk weight. Red nodes = Critical risk. Grey lines = regular transaction links. Dashed Orange lines = suspected money relay chain.")
