"""Logic for Livelihood Recommendation and Family Development Planning.

Public functions (the ones other components may call) must be listed in docs/CONTRACTS.md.
To use the database:  from app.core.database import get_supabase
To use Model 1:       from app.components.livelihood_planning.model_1_recommend.loader import load_model
"""

from app.components.livelihood_planning.model_1_recommend.predict import (
    recommend_with_context,
)
from app.components.livelihood_planning.model_2_swot.swot import (
    build_swot,
    build_swot_report,
)
from app.components.livelihood_planning.model_3_plan.checker import check_plan
from app.components.livelihood_planning.model_3_plan.finance import build_financials
from app.components.livelihood_planning.model_3_plan.retrieval import (
    retrieve_chunks,
)
from app.components.livelihood_planning.model_3_plan.writer import write_plan
from app.components.livelihood_planning.schemas import (
    OFFICIAL_LIVELIHOOD_CATEGORIES,
)


def get_status() -> dict:
    return {"component": "livelihood_planning", "status": "ok"}


def build_swot_response(features: dict) -> dict:
    """Build the complete response shared by SWOT-related API workflows."""
    recommendation_result = recommend_with_context(features)
    recommendations = recommendation_result["recommendations"]
    livelihood = recommendations[0]["livelihood"]
    swot_result = build_swot_report(livelihood, features)
    notes = list(
        dict.fromkeys(
            [*recommendation_result["notes"], *swot_result["notes"]]
        )
    )
    return {
        "recommendations": recommendations,
        "swot": swot_result["swot"],
        "viability": swot_result["viability"],
        "confidence": (
            "low"
            if recommendation_result["confidence"] == "low"
            or swot_result["confidence"] == "low"
            else "normal"
        ),
        "notes": notes,
        "placeholder": False,
    }


def recommend_livelihood(features: dict) -> dict:
    """Build real recommendations and SWOT with placeholder plan content."""
    recommendation_result = recommend_with_context(features)
    recommendations = recommendation_result["recommendations"]
    livelihood = (
        recommendations[0]["livelihood"]
        if recommendations
        else OFFICIAL_LIVELIHOOD_CATEGORIES[-1]
    )
    swot = build_swot(livelihood, features)
    financials = build_financials(livelihood, features)
    chunks = retrieve_chunks(f"{livelihood} livelihood business plan")
    context = [str(chunk["text"]) for chunk in chunks if chunk.get("text")]
    plan = write_plan(livelihood, swot, financials, context)
    plan["validation"] = check_plan(plan)

    return {
        "recommendations": recommendations,
        "swot": swot,
        "plan": plan,
        "placeholder": True,
        "confidence": recommendation_result["confidence"],
        "notes": recommendation_result["notes"],
    }
