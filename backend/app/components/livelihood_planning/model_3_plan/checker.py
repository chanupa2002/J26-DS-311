"""Check generated plan sections and numbers against future realistic ranges."""


def check_plan(plan: dict) -> dict:
    """Report missing required sections using a placeholder structural check."""
    required_sections = ("summary", "market_strategy", "operations", "financials")
    issues = [
        f"Missing required section: {section}"
        for section in required_sections
        if section not in plan
    ]
    return {"ok": not issues, "issues": issues}
