"""market_risk v2 endpoints, served under /api/risk/v2 through the existing v1 router."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Path, Query

from app.components.market_risk.v2 import artifacts, decisions, knowledge, pipeline, service
from app.components.market_risk.v2.schemas import (
    HOUSEHOLD_KEY_PATTERN,
    MONTH_PATTERN,
    DecisionRequest,
    DecisionResponse,
    EvidenceResponse,
    HouseholdDetailResponse,
    HouseholdListResponse,
    MarketTableResponse,
    RecommendationsResponse,
    VisitRequest,
    VisitResponse,
)

logger = logging.getLogger(__name__)

UNAVAILABLE = {503: {"description": "Artifacts missing, version mismatch, or month outside the market data"}}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    artifacts.check_on_startup()
    knowledge.check_on_startup()
    yield


router = APIRouter(prefix="/v2", lifespan=lifespan)  # tags come from the parent "Market Risk" router


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


RULE_ID_PATTERN = r"^[A-Z][0-9]{1,3}$"
RECOMMENDATION_ERRORS = {
    **UNAVAILABLE,
    404: {"description": "Unknown household (or rule not recommended for it)"},
}


def _recommendation_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, knowledge.KnowledgeUnavailable):
        return HTTPException(status_code=503, detail=f"Recommendations are unavailable: {exc}")
    if isinstance(exc, artifacts.ArtifactsUnavailable):
        return _unavailable(exc)
    if isinstance(exc, pipeline.ExplanationError):
        logger.error("market_risk v2: SHAP consistency check failed")
        return HTTPException(status_code=503, detail="Market-risk v2 explanation is unavailable.")
    if isinstance(exc, service.HouseholdNotFound):
        return HTTPException(status_code=404, detail="Household not found.")
    if isinstance(exc, service.RuleNotRecommended):
        return HTTPException(status_code=404, detail="This rule is not recommended for this household now.")
    if isinstance(exc, decisions.DecisionStoreError):
        return HTTPException(status_code=503, detail=str(exc))
    raise exc


_HANDLED = (knowledge.KnowledgeUnavailable, artifacts.ArtifactsUnavailable, pipeline.ExplanationError,
            service.HouseholdNotFound, service.RuleNotRecommended, decisions.DecisionStoreError)


@router.get(
    "/households/{household_key}/recommendations",
    response_model=RecommendationsResponse,
    summary="Evidence-grounded recommendations for a simulated household",
    description=(
        "One follow-up rule (Level A) and the matching action rules (Level B, SHAP-linked first) from "
        "the rule table, each with the top 2 passages of its official circulars. An LLM summary is added "
        "only when a key is configured. Draft rules are marked `draft: true`."
    ),
    responses=RECOMMENDATION_ERRORS,
)
def household_recommendations(household_key: str = Path(pattern=HOUSEHOLD_KEY_PATTERN)) -> dict:
    try:
        return service.recommendations(household_key)
    except _HANDLED as exc:
        raise _recommendation_errors(exc) from None


@router.post(
    "/households/{household_key}/recommendations/{rule_id}/decision",
    response_model=DecisionResponse,
    summary="Record the officer's decision on a recommendation (accept, modify or reject)",
    responses=RECOMMENDATION_ERRORS,
)
def record_decision(
    body: DecisionRequest,
    household_key: str = Path(pattern=HOUSEHOLD_KEY_PATTERN),
    rule_id: str = Path(pattern=RULE_ID_PATTERN),
) -> dict:
    try:
        return service.record_decision(
            household_key, rule_id, body.decision, body.note,
            body.planned_visit_date.isoformat() if body.planned_visit_date else None,
        )
    except _HANDLED as exc:
        raise _recommendation_errors(exc) from None
