"""API endpoints for Livelihood Recommendation and Family Development Planning. Owner edits this file only."""
from fastapi import APIRouter

from app.components.livelihood_planning import services
from app.components.livelihood_planning.schemas import HealthResponse

router = APIRouter(prefix="/api/livelihood", tags=["Livelihood Planning"])


@router.get("/health", response_model=HealthResponse)
def health():
    return services.get_status()
