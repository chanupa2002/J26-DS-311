"""market_risk v2 endpoints, served under /api/risk/v2 through the existing v1 router."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Path, Query

from app.components.market_risk.v2 import artifacts, pipeline, service
from app.components.market_risk.v2.schemas import (
    HOUSEHOLD_KEY_PATTERN,
    MONTH_PATTERN,
    EvidenceResponse,
    HouseholdDetailResponse,
    HouseholdListResponse,
    MarketTableResponse,
    VisitRequest,
    VisitResponse,
)

logger = logging.getLogger(__name__)

UNAVAILABLE = {503: {"description": "Artifacts missing, version mismatch, or month outside the market data"}}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    artifacts.check_on_startup()
    yield


router = APIRouter(prefix="/v2", tags=["Market Risk v2"], lifespan=lifespan)


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=f"Market-risk v2 is unavailable: {exc}")


@router.post(
    "/risk/visit",
    response_model=VisitResponse,
    summary="Score one monitoring visit",
    description=(
        "Returns current risk with reasons, 3M and 6M P(High), class and alert, the top 5 SHAP "
        "factors for the 3M warning, and the market level. Nothing is stored. Real visits "
        "(`is_synthetic: false`) are scored without history and marked `indicative - no history`."
    ),
    responses=UNAVAILABLE,
)
def score_visit(request: VisitRequest) -> dict:
    try:
        return service.score_visit(request)
    except (artifacts.ArtifactsUnavailable, service.MarketDataUnavailable) as exc:
        raise _unavailable(exc) from None
    except pipeline.ExplanationError:
        logger.error("market_risk v2: SHAP consistency check failed")
        raise HTTPException(status_code=503, detail="Market-risk v2 explanation is unavailable.") from None
    except service.UnknownValue as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception as exc:  # type only: the request may be a real visit
        logger.error("market_risk v2: scoring failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="The visit could not be scored.") from None


@router.get(
    "/risk/households",
    response_model=HouseholdListResponse,
    summary="Dashboard list of simulated households for a month",
    responses=UNAVAILABLE,
)
def households(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN, description="YYYY-MM; default is the latest month."),
) -> dict:
    try:
        return service.list_households(month)
    except (artifacts.ArtifactsUnavailable, service.MarketDataUnavailable) as exc:
        raise _unavailable(exc) from None


@router.get(
    "/risk/household/{household_key}",
    response_model=HouseholdDetailResponse,
    summary="Latest visit and visit timeline of a simulated household",
    responses={**UNAVAILABLE, 404: {"description": "Unknown household"}},
)
def household(household_key: str = Path(pattern=HOUSEHOLD_KEY_PATTERN)) -> dict:
    try:
        return service.household_detail(household_key)
    except artifacts.ArtifactsUnavailable as exc:
        raise _unavailable(exc) from None
    except pipeline.ExplanationError:
        logger.error("market_risk v2: SHAP consistency check failed")
        raise HTTPException(status_code=503, detail="Market-risk v2 explanation is unavailable.") from None
    except service.HouseholdNotFound:
        raise HTTPException(status_code=404, detail="Household not found.") from None


@router.get(
    "/market/districts",
    response_model=MarketTableResponse,
    summary="Market pressure for 25 districts and 9 categories in a month",
    responses=UNAVAILABLE,
)
def market_districts(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN, description="YYYY-MM; default is the latest month."),
) -> dict:
    try:
        return service.market_table(month)
    except (artifacts.ArtifactsUnavailable, service.MarketDataUnavailable) as exc:
        raise _unavailable(exc) from None


@router.get(
    "/model/evidence",
    response_model=EvidenceResponse,
    summary="Test results against persistence, thresholds and limitations",
    responses=UNAVAILABLE,
)
def model_evidence() -> dict:
    try:
        return service.model_evidence()
    except artifacts.ArtifactsUnavailable as exc:
        raise _unavailable(exc) from None
