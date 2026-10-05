"""API endpoints for Explainable Market-Risk Prediction, Recommendation and Decision Dashboard. Owner edits this file only."""
from fastapi import APIRouter

from app.components.market_risk import services
from app.components.market_risk.schemas import HealthResponse

router = APIRouter(prefix="/api/risk", tags=["Market Risk"])


@router.get("/health", response_model=HealthResponse)
def health():
    return services.get_status()
