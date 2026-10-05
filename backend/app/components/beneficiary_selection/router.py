"""API endpoints for Beneficiary Selection Support. Owner edits this file only."""
from fastapi import APIRouter

from app.components.beneficiary_selection import services
from app.components.beneficiary_selection.schemas import HealthResponse

router = APIRouter(prefix="/api/beneficiary", tags=["Beneficiary Selection"])


@router.get("/health", response_model=HealthResponse)
def health():
    return services.get_status()
