"""API endpoints for Livelihood Recommendation and Family Development Planning. Owner edits this file only."""
from fastapi import APIRouter, HTTPException

from app.components.livelihood_planning import services
from app.components.livelihood_planning.schemas import (
    AssessmentRequest,
    AssessmentResponse,
    BeneficiarySummary,
    HealthResponse,
    LivelihoodRequest,
    PlanResponse,
    RecommendResponse,
    SwotRequest,
    SwotResponse,
)
from app.core.database import get_supabase

router = APIRouter(prefix="/api/livelihood", tags=["Livelihood Planning"])
BENEFICIARY_FEATURE_FIELDS = (
    "district",
    "ds_division",
    "age",
    "gender",
    "female_headed",
    "disability",
    "aswesuma_category",
)
BENEFICIARY_SUMMARY_COLUMNS = (
    "id,full_name,district,age,gender,female_headed,disability,"
    "aswesuma_category,is_demo"
)
BENEFICIARY_ASSESSMENT_COLUMNS = (
    "id,full_name,district,ds_division,age,gender,female_headed,"
    "disability,aswesuma_category,is_demo"
)
DATABASE_UNAVAILABLE_MESSAGE = "Database service is temporarily unavailable."


def _database_unavailable(exception: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=DATABASE_UNAVAILABLE_MESSAGE,
    )


def _request_features(
    request: LivelihoodRequest | SwotRequest,
) -> tuple[dict, str | None]:
    values = request.model_dump(exclude_none=True)
    return values, values.pop("livelihood", None)


def _invalid_livelihood(exception: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exception))


@router.get("/health", response_model=HealthResponse)
def health():
    return services.get_status()


@router.post("/recommend", response_model=RecommendResponse)
def recommend(request: LivelihoodRequest) -> dict:
    features, _ = _request_features(request)
    result = services.build_recommendation_response(features)
    return {
        **result,
        "placeholder": False,
    }


@router.post("/swot", response_model=SwotResponse)
def swot(request: SwotRequest) -> dict:
    features, requested_livelihood = _request_features(request)
    try:
        if requested_livelihood is None:
            return services.build_swot_response(features)
        return services.build_swot_response(features, requested_livelihood)
    except services.InvalidLivelihoodSelection as exception:
        raise _invalid_livelihood(exception) from exception


@router.get("/beneficiaries", response_model=list[BeneficiarySummary])
def beneficiaries() -> list[dict]:
    try:
        response = (
            get_supabase()
            .table("beneficiaries")
            .select(BENEFICIARY_SUMMARY_COLUMNS)
            .execute()
        )
    except Exception as exception:
        raise _database_unavailable(exception) from exception
    return response.data or []


@router.post(
    "/assess/{beneficiary_id}", response_model=AssessmentResponse
)
def assess_beneficiary(
    beneficiary_id: str, request: AssessmentRequest | None = None
) -> dict:
    try:
        client = get_supabase()
        response = (
            client.table("beneficiaries")
            .select(BENEFICIARY_ASSESSMENT_COLUMNS)
            .eq("id", beneficiary_id)
            .limit(1)
            .execute()
        )
    except Exception as exception:
        raise _database_unavailable(exception) from exception
    rows = response.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Beneficiary not found.")

    beneficiary = rows[0]
    features = {
        field: beneficiary[field]
        for field in BENEFICIARY_FEATURE_FIELDS
        if beneficiary.get(field) is not None
    }
    requested_livelihood = request.livelihood if request else None
    try:
        if requested_livelihood is None:
            swot_response = services.build_swot_response(features)
        else:
            swot_response = services.build_swot_response(
                features, requested_livelihood
            )
    except services.InvalidLivelihoodSelection as exception:
        raise _invalid_livelihood(exception) from exception
    recommendations = swot_response["recommendations"]
    payload = {
        "beneficiary_id": beneficiary["id"],
        "input_snapshot": features,
        "recommendations": recommendations,
        "chosen_livelihood": (
            recommendations[0]["livelihood"] if recommendations else None
        ),
        "swot": swot_response["swot"],
        "viability": swot_response["viability"],
        "notes": swot_response["notes"],
        "confidence": swot_response["confidence"],
        "decision_trail": swot_response["decision_trail"],
        "status": "draft",
    }
    try:
        saved_rows = (
            client.table("livelihood_assessments")
            .insert(payload)
            .execute()
            .data
            or []
        )
    except Exception as exception:
        raise _database_unavailable(exception) from exception
    if not saved_rows:
        raise HTTPException(
            status_code=503,
            detail=DATABASE_UNAVAILABLE_MESSAGE,
        )
    return {
        **saved_rows[0],
        "selected_livelihood": swot_response["selected_livelihood"],
        "viability_preview": swot_response["viability_preview"],
    }


@router.get(
    "/assessments/{beneficiary_id}",
    response_model=list[AssessmentResponse],
)
def assessment_history(beneficiary_id: str) -> list[dict]:
    try:
        response = (
            get_supabase()
            .table("livelihood_assessments")
            .select("*")
            .eq("beneficiary_id", beneficiary_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exception:
        raise _database_unavailable(exception) from exception
    return response.data or []


@router.post("/plan", response_model=PlanResponse)
def plan(request: LivelihoodRequest) -> dict:
    features, _ = _request_features(request)
    return services.recommend_livelihood(features)
