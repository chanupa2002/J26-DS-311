"""API endpoints for Explainable Evidence Trust Scoring and Recommendation Framework. Owner edits this file only."""
from fastapi import APIRouter

from app.components.evidence_trust import services
from app.components.evidence_trust.schemas import HealthResponse

router = APIRouter(prefix="/api/trust", tags=["Evidence Trust"])


@router.get("/health", response_model=HealthResponse)
def health():
    return services.get_status()
