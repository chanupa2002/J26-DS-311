"""API endpoints for Explainable Market-Risk Prediction, Recommendation and Decision Dashboard. Owner edits this file only."""
import logging

from fastapi import APIRouter, HTTPException, Query

from app.components.market_risk import services
from app.components.market_risk.ml.explainer import ExplanationError
from app.components.market_risk.schemas import (
    ExplainRequest,
    ExplainResponse,
    HealthResponse,
    HistoryFeaturesRequest,
    HistoryFeaturesResponse,
    Horizon,
    IdentifyRequest,
    IdentifyResponse,
    MarketContextResponse,
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
)

router = APIRouter(prefix="/api/risk", tags=["Market Risk"])
logger = logging.getLogger(__name__)

# Response for the IdentifyRequest schema example (shown in /docs; checked by tests).
IDENTIFY_EXAMPLE_RESPONSE = {
    "risk_class": "Unassigned",
    "risk_ord": None,
    "signal_count": 1,
    "unknown_count": 1,
    "reasons": [
        "No profit last month",
        "Not answered: market stress",
        "Blank answers could change the class -> Unassigned",
        "Could be up to High if blank answers are Yes; follow-up visit recommended",
    ],
    "rule_version": "SUSTAIN-HH-Risk-Rule v1.0 (provisional, requires expert validation)",
    "best_case_class": "Medium",
    "worst_case_class": "High",
    "possible_range": "Medium-High",
    "follow_up_needed": True,
}

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
    elif isinstance(exc, ImportError):
        reason = "the SHAP explanation library is not installed on the server"
    elif isinstance(exc, ExplanationError):
        reason = "the SHAP explanation failed a consistency check"
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


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Explain 3-month and/or 6-month predictions with SHAP",
    description=(
        "Same input as `/api/risk/predict` (all 53 `F_*` features, `horizon`) "
        "plus `top_k` (1-20, default 5). For each horizon it returns the "
        "predicted class with its SHAP `base_value`, `probability` and "
        "`top_factors`, the summed `other_features_contribution`, and "
        "`high_risk_factors`. For every class, base_value + all contributions "
        "= the model probability.\n\n"
        "**`high_risk_factors` are the easiest to read: `+` pushes towards "
        "High, `-` pushes away from High.** In `top_factors`, `contribution` "
        "is towards the *predicted* class (for a Low prediction, `+` means "
        "towards Low). `direction` always describes the effect on the expected "
        "risk score 0*P(Low) + 1*P(Medium) + 2*P(High).\n\n"
        "**SHAP explains what drives the model, not real-world causes.** "
        f"**{NOT_READY_NOTE}**"
    ),
    responses={503: {"description": "Model files, SHAP library or explanation unavailable"}},
)
def explain(request: ExplainRequest) -> ExplainResponse:
    try:
        return services.explain_market_risk(request)
    except (FileNotFoundError, RuntimeError, ImportError) as exc:
        raise _model_unavailable(exc) from None


@router.post(
    "/identify",
    response_model=IdentifyResponse,
    summary="Identify a household's current risk class (rule-based)",
    description=(
        "Applies SUSTAIN-HH-Risk-Rule v1.0 to the current visit. This is "
        "**rule-based, not an ML model**, and the rule is **provisional (not yet "
        "validated by experts)**.\n\n"
        "Send all four signals, each `0`, `1` or `null` (not answered); extra "
        "keys are rejected with 422. High = business not running, or 2+ of "
        "{no profit last month, not progressing well, market stress}; Medium = "
        "exactly one; Low = business running and all three answered 0; "
        "Unassigned = blanks could change the class, or business status blank "
        "(unless the signals alone already give High).\n\n"
        "To show how bad an Unassigned case could be, the response also has "
        "`best_case_class` (every blank = No, business running), "
        "`worst_case_class` (every blank = Yes, business not running), "
        "`possible_range` (e.g. `Medium-High`) and `follow_up_needed` (true "
        "when Unassigned). For assigned cases both bounds equal `risk_class`.\n\n"
        "`risk_ord`, `signal_count` and `unknown_count` can be used as "
        "`F_Risk_Ord_t`, `F_Risk_Signal_Count_t` and `F_Risk_Unknown_t` in "
        "`/api/risk/predict`."
    ),
    responses={
        200: {"content": {"application/json": {"example": IDENTIFY_EXAMPLE_RESPONSE}}}
    },
)
def identify(request: IdentifyRequest) -> IdentifyResponse:
    return services.identify_current_risk(request)


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


@router.get(
    "/market-context",
    response_model=MarketContextResponse,
    summary="Market and macro features for a category and month",
    description=(
        "Returns the 8 `F_Mkt_*` features (by category and month) and the 5 "
        "`F_Macro_*` features (by month) that `/api/risk/predict` needs. A field "
        "officer cannot know these, so the frontend fills them from here. Values "
        "come from `ml/market_context.json`, built with the same join and "
        "formulas as model training (aggregated public indicators only).\n\n"
        "`category` is a trained `F_Category` level (any case) or an upper-case "
        "survey name such as `TRADE`; unknown categories return 422. `month` is "
        "`YYYY-MM`. Months outside the data return 200 with every value null, "
        "`in_data_range: false` and a note (values are never guessed). Without "
        "category market evidence the market values are null and "
        "`F_Mkt_Evidence_Missing` is 1, as in training."
    ),
    responses={
        422: {"description": "Unknown category or badly formatted month"},
        503: {"description": "Lookup file missing on the server"},
    },
)
def market_context_lookup(
    category: str = Query(min_length=1, description="Trained F_Category level or upper-case survey name"),
    month: str = Query(pattern=services.MONTH_PATTERN, description="Month as YYYY-MM"),
) -> MarketContextResponse:
    try:
        return services.get_market_context(category, month)
    except services.UnknownCategoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except FileNotFoundError as exc:
        logger.error("market_risk market context unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Market-context data is unavailable on the server. Contact the market_risk owner.",
        ) from None


@router.post(
    "/history-features",
    response_model=HistoryFeaturesResponse,
    summary="Compute the 14 history features from earlier visits",
    description=(
        "Field officers cannot know values such as `F_Risk_Mean_3M_Window`, so this "
        "computes the 14 history features for `/api/risk/predict` from simple "
        "answers, with the **same code as model training**. Send `current_visit` "
        "(`visit_date` and `grant_date` as YYYY-MM-DD, plus `business_running`, "
        "`profit_last_month`, `progressing_well`, `market_stress`, each 1, 0 or "
        "null) and 0 to 12 `previous_visits` (`month` YYYY-MM and the same 4 "
        "answers). No household IDs or names. Each visit's risk class comes from "
        "SUSTAIN-HH-Risk-Rule v1.0 (as `/identify`). With no previous visits the "
        "result equals the training values for a first visit.\n\n"
        "422 for a bad date or month, duplicate months, a previous visit not "
        "before the visit_date month, grant_date after visit_date, or more than "
        "12 previous visits."
    ),
)
def history_features(request: HistoryFeaturesRequest) -> HistoryFeaturesResponse:
    return services.compute_history_features(request)
