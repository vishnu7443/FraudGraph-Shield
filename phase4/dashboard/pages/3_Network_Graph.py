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
st.caption("Interactive relay chain visualization — colored by mule probability score")

account_id = st.session_state.get("graph_account", 1247)
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

# PyVis network setup
net = Network(
    height="600px", width="100%",
    bgcolor="#0F1117",         # dark background — looks great on projectors
    font_color="white",
    directed=True
)
net.set_options("""
{
  "physics": {
    "enabled": true,
    "stabilization": {"iterations": 100}
  },
  "edges": {
    "arrows": {"to": {"enabled": true, "scaleFactor": 1.2}},
    "color": {"color": "#555555"},
    "width": 2
  }
}
""")

def score_to_color(score: float) -> str:
    if score >= 0.8:    return "#C00000"   # deep red — critical
    elif score >= 0.65: return "#FF6B00" # orange — high
    elif score >= 0.4:  return "#FFC107" # amber — medium
    else:               return "#2E7D32" # green — low

def score_to_size(score: float) -> int:
    return int(20 + score * 40)          # bigger node = higher risk

root_id = cluster["root_account_id"]
nodes   = cluster["cluster_nodes"]

# Add root node explicitly if not present in the GNN nodes list to prevent AssertionError
has_root = any(node["account_id"] == root_id for node in nodes)
if not has_root:
    net.add_node(
        root_id,
        label=f"Acc #{root_id}\n(Root)",
        color={"background": "#C00000", "border": "#FFFFFF"},
        size=35,
        title=f"Root Account: {root_id}\nRisk: Root Target Node",
        borderWidth=3
    )

# Add nodes
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

# Add edges — root connects to all
for i, node in enumerate(nodes):
    target_id = node["account_id"]
    if target_id != root_id:
        m_score = node.get("mule_score", node.get("composite_score", 0.0))
        norm_m_score = m_score / 100.0 if m_score > 1.0 else m_score
        
        net.add_edge(root_id, target_id,
                     title=f"Relay link",
                     width=max(1, int(norm_m_score * 4)))

# Chain edges — simulate money relay sequence
for i in range(len(nodes) - 1):
    source_id = nodes[i]["account_id"]
    target_id = nodes[i+1]["account_id"]
    if source_id != target_id:
        net.add_edge(
            source_id,
            target_id,
            color="#FF6B00",
            dashes=True,
            title="Suspected relay"
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
col1.metric("Accounts in Cluster", len(nodes))
col2.metric("Cluster Risk Score",  f"{norm_cluster_risk:.3f}")
col3.metric("Relay Chain", "🚨 DETECTED" if relay else "✅ None")

if relay:
    st.error("⚠️ Money relay chain detected. Recommend immediate freeze of all cluster accounts.")

st.divider()
components.html(html, height=620, scrolling=False)
st.caption("Node size = risk level. Red = Critical. Dashed edges = suspected relay path.")
