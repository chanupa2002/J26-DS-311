"""API endpoints for Explainable Market-Risk Prediction, Recommendation and Decision Dashboard. Owner edits this file only."""
import logging

from fastapi import APIRouter, HTTPException

from app.components.market_risk import services
from app.components.market_risk.schemas import (
    HealthResponse,
    Horizon,
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
)

router = APIRouter(prefix="/api/risk", tags=["Market Risk"])
logger = logging.getLogger(__name__)

NOT_READY_NOTE = (
    "Both models are currently NOT_READY: they were trained and tested on "
    "synthetic data only. Every result includes model_status and "
    "deployment_reason, which must be shown to users."
)


def _model_unavailable(exc: Exception) -> HTTPException:
    """Log the full error server-side; return a 503 without paths or traces."""
    logger.error("market_risk model unavailable: %s", exc, exc_info=True)
    if isinstance(exc, FileNotFoundError):
        reason = "model files are missing on the server"
    else:
        reason = (
            "the model could not be loaded (scikit-learn version mismatch "
            "or model/metadata mismatch)"
        )
    return HTTPException(
        status_code=503,
        detail=f"Market-risk model is unavailable: {reason}. Contact the market_risk owner.",
    )


@router.get("/health", response_model=HealthResponse)
def health():
    return services.get_status()


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Predict 3-month and/or 6-month household market risk",
    description=(
        "Send `horizon` (`3M`, `6M` or `both`) and all 53 engineered `F_*` "
        "features. Every feature key is required; any value may be null "
        "(numeric nulls are median-imputed). Unknown keys are rejected with "
        "422. `F_Category` also accepts upper-case survey names such as "
        "`TRADE`, which are converted with a warning. Unknown categories are "
        "accepted with a warning.\n\n"
        f"**{NOT_READY_NOTE}**"
    ),
    responses={503: {"description": "Model files missing or cannot be loaded"}},
)
def predict(request: PredictRequest) -> PredictResponse:
    try:
        return services.predict_market_risk(request)
    except (FileNotFoundError, RuntimeError) as exc:
        raise _model_unavailable(exc) from None


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Describe the market-risk models and their input features",
    description=(
        "Returns model metadata (status, metrics, training period), the 53 "
        "input features and the allowed category levels. Omit `horizon` to "
        "get both models. Does not load the model files.\n\n"
        f"**{NOT_READY_NOTE}**"
    ),
    responses={503: {"description": "Model metadata files missing"}},
)
def model_info(horizon: Horizon | None = None) -> ModelInfoResponse:
    try:
        return services.get_model_info(horizon)
    except (FileNotFoundError, RuntimeError) as exc:
        raise _model_unavailable(exc) from None
