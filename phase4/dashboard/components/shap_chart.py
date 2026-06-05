# phase4/dashboard/components/shap_chart.py
#
# SHAP explanation chart component. Renders a horizontal bar chart displaying
# features that increase risk (in red) and features that decrease risk (in green).

# pyrefly: ignore [missing-import]
import plotly.graph_objects as go
import pandas as pd

FEATURE_LABELS = {
    "peer_deviation_composite": "Peer Activity Deviation",
    "tenure_days": "Account Tenure (Days)",
    "product_complexity": "Product Complexity Score",
    "F3891": "Occupation Risk Factor",
    "F3886": "Account Profiling Behavior",
    "is_round_amount": "Transaction Roundness Anomaly",
    "is_new_counterparty": "New Counterparty Flag",
    "hour_of_day": "Transaction Hour",
    "channel": "Payment Channel (UPI/RTGS)"
}

def render_shap_chart(shap_factors: list) -> go.Figure:
    """Returns a Plotly Figure showing SHAP feature contributions to the score."""
    if not shap_factors:
        # Empty placeholder state figure
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text="No explanation data available", showarrow=False, font_size=14, font_color="#9ca3af")],
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=200
        )
        return fig
        
    df = pd.DataFrame(shap_factors)
    
    # Map feature names to clean labels
    df["label"] = df["feature_name"].apply(lambda x: FEATURE_LABELS.get(x, f"Feature {x}"))
    
    # Sort so highest contribution is at the top of the chart
    df = df.sort_values(by="contribution", ascending=True)
    
    # Color mapping: Positive -> Crimson, Negative -> Green/Blue
    colors = df["contribution"].apply(lambda x: "rgba(239, 68, 68, 0.75)" if x >= 0 else "rgba(16, 185, 129, 0.75)")
    border_colors = df["contribution"].apply(lambda x: "#ef4444" if x >= 0 else "#10b981")
    
    fig = go.Figure(go.Bar(
        x = df["contribution"],
        y = df["label"],
        orientation = 'h',
        marker = dict(
            color = colors,
            line = dict(color=border_colors, width=1.5)
        ),
        hovertemplate = "<b>%{y}</b><br>Impact: %{x:+.4f}<extra></extra>"
    ))
    
    # Add vertical line at 0.0
    fig.add_shape(
        type="line",
        x0=0, y0=-0.5, x1=0, y1=len(df)-0.5,
        line=dict(color="#4b5563", width=1.5, dash="dash")
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10),
        height=220 + (len(df) * 10),
        xaxis=dict(
            title=dict(
                text="SHAP Feature Value Impact",
                font=dict(size=12, color="#9ca3af", family="Inter, sans-serif")
            ),
            gridcolor="rgba(75, 85, 99, 0.15)",
            tickfont=dict(color="#9ca3af", size=10),
            zeroline=False
        ),
        yaxis=dict(
            tickfont=dict(color="#ffffff", size=11, family="Inter, sans-serif"),
            gridcolor="rgba(0,0,0,0)"
        )
    )
    
    return fig
