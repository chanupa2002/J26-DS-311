"""API endpoints for Livelihood Recommendation and Family Development Planning. Owner edits this file only."""
from fastapi import APIRouter

from app.components.livelihood_planning import services
from app.components.livelihood_planning.model_1_recommend.predict import (
    recommend_with_context,
)
from app.components.livelihood_planning.model_2_swot.swot import build_swot
from app.components.livelihood_planning.schemas import (
    HealthResponse,
    LivelihoodRequest,
    PlanResponse,
    RecommendResponse,
    SwotResponse,
)

router = APIRouter(prefix="/api/livelihood", tags=["Livelihood Planning"])


@router.get("/health", response_model=HealthResponse)
def health():
    return services.get_status()


@router.post("/recommend", response_model=RecommendResponse)
def recommend(request: LivelihoodRequest) -> dict:
    features = request.model_dump(exclude_none=True)
    result = recommend_with_context(features)
    return {
        **result,
        "placeholder": False,
    }


@router.post("/swot", response_model=SwotResponse)
def swot(request: LivelihoodRequest) -> dict:
    features = request.model_dump(exclude_none=True)
    result = recommend_with_context(features)
    recommendations = result["recommendations"]
    livelihood = recommendations[0]["livelihood"]
    return {
        **result,
        "swot": build_swot(livelihood, features),
        "placeholder": True,
    }


@router.post("/plan", response_model=PlanResponse)
def plan(request: LivelihoodRequest) -> dict:
    features = request.model_dump(exclude_none=True)
    return services.recommend_livelihood(features)
