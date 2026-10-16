"""Calculate business-plan financial values in deterministic Python code."""


def build_financials(livelihood: str, features: dict) -> dict:
    """Return clearly marked dummy financial values."""
    _ = features
    return {
        "livelihood": livelihood,
        "currency": "LKR",
        "startup_cost": 0.0,
        "monthly_revenue": 0.0,
        "monthly_cost": 0.0,
        "monthly_profit": 0.0,
        "placeholder": True,
    }
