# phase4/dashboard/components/action_badge.py
#
# Custom HTML/CSS styling for risk levels and automated actions.
# Creates premium looking pill badges with custom hex colors.

def get_action_badge(action: str) -> str:
    """Returns HTML representation of a premium action badge."""
    action = action.upper()
    
    # Styles for each action
    styles = {
        "ALLOW": {
            "bg": "rgba(16, 185, 129, 0.15)",  # Emerald Green
            "border": "#10b981",
            "text": "#10b981",
            "shadow": "0 0 10px rgba(16, 185, 129, 0.2)"
        },
        "MONITOR": {
            "bg": "rgba(245, 158, 11, 0.15)", # Amber/Yellow
            "border": "#f59e0b",
            "text": "#f59e0b",
            "shadow": "0 0 10px rgba(245, 158, 11, 0.2)"
        },
        "HOLD": {
            "bg": "rgba(249, 115, 22, 0.15)",  # Orange
            "border": "#f97316",
            "text": "#f97316",
            "shadow": "0 0 10px rgba(249, 115, 22, 0.2)"
        },
        "BLOCK": {
            "bg": "rgba(239, 68, 68, 0.18)",   # Crimson Red
            "border": "#ef4444",
            "text": "#ef4444",
            "shadow": "0 0 15px rgba(239, 68, 68, 0.4)"
        }
    }
    
    style = styles.get(action, styles["ALLOW"])
    
    badge_html = f"""
    <span style="
        display: inline-block;
        padding: 6px 14px;
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 700;
        border-radius: 20px;
        background-color: {style['bg']};
        color: {style['text']};
        border: 1.5px solid {style['border']};
        box-shadow: {style['shadow']};
        text-transform: uppercase;
        letter-spacing: 0.8px;
        text-align: center;
        min-width: 90px;
    ">
        {action}
    </span>
    """
    return badge_html

def get_risk_tier_badge(tier: str) -> str:
    """Returns HTML representation of a premium risk tier badge."""
    tier = tier.upper()
    
    # Styles for each risk tier
    styles = {
        "LOW": {
            "bg": "rgba(59, 130, 246, 0.15)",   # Bright Blue
            "border": "#3b82f6",
            "text": "#3b82f6",
            "shadow": "0 0 8px rgba(59, 130, 246, 0.15)"
        },
        "MEDIUM": {
            "bg": "rgba(245, 158, 11, 0.15)",  # Amber
            "border": "#f59e0b",
            "text": "#f59e0b",
            "shadow": "0 0 8px rgba(245, 158, 11, 0.15)"
        },
        "HIGH": {
            "bg": "rgba(249, 115, 22, 0.15)",   # Orange
            "border": "#f97316",
            "text": "#f97316",
            "shadow": "0 0 10px rgba(249, 115, 22, 0.2)"
        },
        "CRITICAL": {
            "bg": "rgba(220, 38, 38, 0.18)",   # Crimson Red
            "border": "#dc2626",
            "text": "#dc2626",
            "shadow": "0 0 15px rgba(220, 38, 38, 0.35)"
        }
    }
    
    style = styles.get(tier, styles["LOW"])
    
    badge_html = f"""
    <span style="
        display: inline-block;
        padding: 5px 12px;
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        font-weight: 600;
        border-radius: 15px;
        background-color: {style['bg']};
        color: {style['text']};
        border: 1px solid {style['border']};
        box-shadow: {style['shadow']};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        text-align: center;
    ">
        {tier}
    </span>
    """
    return badge_html
