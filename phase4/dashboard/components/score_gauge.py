# phase4/dashboard/components/score_gauge.py
#
# Score gauge component using Plotly. Renders a stunning radial speed-like
# indicator colored dynamically based on the composite score thresholds.

# pyrefly: ignore [missing-import]
import plotly.graph_objects as go

def render_score_gauge(score: float) -> go.Figure:
    """Returns a Plotly Figure rendering a beautiful risk score gauge."""
    
    # Determine color of indicator bar based on score ranges
    if score < 40:
        bar_color = "#3b82f6"  # Blue (Low)
        title_text = "LOW RISK"
    elif score < 65:
        bar_color = "#f59e0b"  # Amber (Medium)
        title_text = "MEDIUM RISK"
    elif score < 80:
        bar_color = "#f97316"  # Orange (High)
        title_text = "HIGH RISK"
    else:
        bar_color = "#ef4444"  # Crimson (Critical)
        title_text = "CRITICAL RISK"
        
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {
            'text': f"<span style='font-size:16px; font-weight:700; color:{bar_color}; letter-spacing:1px;'>{title_text}</span>",
            'font': {'family': "Inter, sans-serif"}
        },
        number = {
            'font': {'size': 54, 'color': '#ffffff', 'family': 'Inter, sans-serif', 'weight': 'bold'},
            'suffix': ""
        },
        gauge = {
            'axis': {
                'range': [0, 100], 
                'tickwidth': 1.5, 
                'tickcolor': "#4b5563",
                'tickvals': [0, 20, 40, 60, 80, 100],
                'ticktext': ["0", "20", "40", "60", "80", "100"]
            },
            'bar': {'color': bar_color, 'thickness': 0.75},
            'bgcolor': "rgba(31, 41, 55, 0.5)",
            'borderwidth': 1.5,
            'bordercolor': "#4b5563",
            'steps': [
                {'range': [0, 40], 'color': 'rgba(59, 130, 246, 0.05)'},
                {'range': [40, 65], 'color': 'rgba(245, 158, 11, 0.05)'},
                {'range': [65, 80], 'color': 'rgba(249, 115, 22, 0.05)'},
                {'range': [80, 100], 'color': 'rgba(239, 68, 68, 0.08)'}
            ],
            'threshold': {
                'line': {'color': "#ef4444", 'width': 3},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=15, r=15, t=50, b=15),
        height=220,
        font={'color': "#ffffff", 'family': "Inter, sans-serif"}
    )
    
    return fig
