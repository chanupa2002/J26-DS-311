"""API endpoints for Explainable Evidence Trust Scoring and Recommendation Framework. Owner edits this file only."""
from fastapi import APIRouter, File, Form, UploadFile

from app.components.evidence_trust import services
from app.components.evidence_trust.schemas import HealthResponse, ImageVerificationResponse

router = APIRouter(prefix="/api/trust", tags=["Evidence Trust"])


@router.get("/health", response_model=HealthResponse)
def health():
    return services.get_status()


@router.post("/verify-image", response_model=ImageVerificationResponse)
async def verify_image(
    image: UploadFile = File(...),
    household_id: str = Form(...),
    month: str = Form(...),
    registered_category: str | None = Form(default=None),
    previous_image_reference: str | None = Form(default=None),
):
    """Verify one uploaded evidence image and return its report."""
    return await services.verify_image_upload(await image.read(), household_id, month, registered_category, previous_image_reference)


@router.post("/category-match")
async def category_match_only(
    image: UploadFile = File(...),
    registered_category: str = Form(...),
):
    """Test only the livelihood category-match model."""
    return await services.verify_category_match(await image.read(), registered_category)


@router.post("/progress-check")
async def progress_check_only(
    previous_image: UploadFile = File(...),
    current_image: UploadFile = File(...),
    household_id: str = Form(...),
    previous_month: str = Form(...),
    current_month: str = Form(...),
    registered_category: str = Form(...),
):
    """Test only month-to-month image progress comparison."""
    return await services.verify_progress_only(
        await previous_image.read(),
        await current_image.read(),
        household_id,
        previous_month,
        current_month,
        registered_category,
    )
