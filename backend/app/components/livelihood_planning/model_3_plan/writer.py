"""Write business-plan sections with Gemini after that integration is approved."""


def write_plan(
    livelihood: str,
    swot: dict,
    financials: dict,
    context: list[str],
) -> dict:
    """Return placeholder plan sections without calling an external API."""
    _ = swot
    return {
        "summary": f"PLACEHOLDER plan summary for {livelihood}.",
        "market_strategy": "PLACEHOLDER market strategy.",
        "operations": "PLACEHOLDER operations plan.",
        "financials": financials,
        "supporting_context": context,
        "placeholder": True,
    }
