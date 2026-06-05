# phase4/dashboard/components/network_viz.py
#
# Custom PyVis component that visualizes mule account networks.
# Assigns node colors according to risk tiers (CRITICAL=Red, HIGH=Orange, etc.)
# and renders interactive tooltips.

from pyvis.network import Network
import tempfile
import os

# Tier Colors mapping
TIER_COLORS = {
    "CRITICAL": "#dc2626", # Crimson Red
    "HIGH": "#f97316",     # Orange
    "MEDIUM": "#f59e0b",   # Amber
    "LOW": "#3b82f6",      # Bright Blue
    "NONE": "#6b7280"      # Gray
}

def generate_network_html(nodes: list, edges: list, root_account_id: int) -> str:
    """Generates and returns the interactive HTML visualization code of the network."""
    
    # Initialize PyVis Network
    net = Network(
        height="480px", 
        width="100%", 
        bgcolor="#0f172a", # Tailwind Slate 900
        font_color="#ffffff",
        directed=True
    )
    
    # Force atlas or basic physics configuration
    net.force_atlas_2based(
        gravity=-50,
        central_gravity=0.01,
        spring_length=120,
        spring_strength=0.08,
        damping=0.4
    )
    
    # Add Nodes
    for node in nodes:
        node_id = node["account_id"]
        tier = node.get("risk_tier", "LOW").upper()
        score = node.get("composite_score", 0.0)
        action = node.get("automated_action", "ALLOW")
        
        # Color based on risk tier
        color = TIER_COLORS.get(tier, TIER_COLORS["LOW"])
        
        # Sizing: larger size for root account being analysed
        size = 32 if node_id == root_account_id else 22
        border_width = 3 if node_id == root_account_id else 1
        
        # Node styling & label
        label = f"Acc: {node_id}\n[{tier}]"
        
        # HTML Tooltip
        title = f"""
        <div style="
            font-family: 'Inter', sans-serif;
            background-color: #1e293b;
            color: #ffffff;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid #475569;
            font-size: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        ">
            <b>Account ID:</b> {node_id}<br/>
            <b>Risk Score:</b> {score:.1f}<br/>
            <b>Risk Tier:</b> <span style="color: {color}; font-weight: bold;">{tier}</span><br/>
            <b>Recommended Action:</b> <b>{action}</b>
        </div>
        """
        
        net.add_node(
            node_id,
            label=label,
            title=title,
            size=size,
            color=color,
            borderWidth=border_width,
            borderWidthSelected=4,
            font={"color": "#ffffff", "size": 11, "face": "Inter"}
        )
        
    # Add Edges
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        channel = edge.get("channel", "UPI")
        amount = edge.get("amount", 0.0)
        
        # Color edges by channel type
        edge_color = "rgba(148, 163, 184, 0.4)" # default slate
        if channel == "UPI":
            edge_color = "rgba(34, 211, 238, 0.6)" # Cyan
        elif channel == "RTGS":
            edge_color = "rgba(168, 85, 247, 0.6)" # Purple
        elif channel == "NEFT":
            edge_color = "rgba(52, 211, 153, 0.6)" # Green
            
        label = f"{channel} (₹{amount:,.0f})"
        
        net.add_edge(
            source,
            target,
            title=label,
            label=channel,
            color=edge_color,
            width=2,
            font={"color": "#94a3b8", "size": 9, "align": "top", "face": "Inter"}
        )
        
    # Generate temporary HTML file to capture the rendered visualization code
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, f"fraudgraph_{root_account_id}.html")
    
    # Save the PyVis graph
    net.write_html(temp_file_path)
    
    # Read the file content
    with open(temp_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # Clean up
    try:
        os.remove(temp_file_path)
    except Exception:
        pass
        
    # Offline customization: Replace standard CDN scripts with offline scripts if needed,
    # but PyVis uses cdnjs by default which is perfect. To make it load beautifully, 
    # we inject a small CSS override to remove margins.
    style_override = """
    <style>
        body { margin: 0; padding: 0; background-color: #0f172a; overflow: hidden; }
        #mynetwork { border: none !important; }
    </style>
    """
    html_content = html_content.replace("<style>", style_override + "<style>")
    
    return html_content
