"""Build a structured SWOT result from livelihood facts and household features."""

from app.components.livelihood_planning.model_2_swot.factors import (
    get_livelihood_factors,
)
from app.components.livelihood_planning.model_2_swot.scoring import score_factors

SWOT_KEYS = ("strengths", "weaknesses", "opportunities", "threats")


def build_swot(livelihood: str, features: dict) -> dict:
    """Return placeholder SWOT groups with text and source fields."""
    factors = get_livelihood_factors(livelihood)
    scored_factors = score_factors(factors, features)
    result: dict[str, list[dict[str, str]]] = {key: [] for key in SWOT_KEYS}

    for factor in scored_factors:
        category = str(factor.get("category", ""))
        if category in result:
            result[category].append(
                {
                    "text": str(factor.get("text", "")),
                    "source": str(factor.get("source", "placeholder")),
                }
            )

    return result
