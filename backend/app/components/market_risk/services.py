"""Logic for Explainable Market-Risk Prediction, Recommendation and Decision Dashboard.

Public functions (the ones other components may call) must be listed in docs/CONTRACTS.md.

predict_market_risk(request) -> PredictResponse
    request is a PredictRequest (or a dict with the same shape):
    {"horizon": "3M" | "6M" | "both", "features": {all 53 F_* keys, values may be null}}.
    Returns per-horizon predicted_risk (Low/Medium/High), probabilities,
    model_status and deployment_reason, plus warnings and placeholder=False.
    Both models are currently NOT_READY (trained on synthetic data); callers must
    show model_status and deployment_reason to users.
    Raises FileNotFoundError / RuntimeError if a model cannot be loaded.

get_model_info(horizon=None) -> ModelInfoResponse
    Model metadata, the 53 input features and the allowed category levels.
    Reads metadata files only; does not load the models.

identify_current_risk(request) -> IdentifyResponse
    request is an IdentifyRequest (or a dict with the same shape):
    {"business_not_running", "no_profit_last_month", "not_progressing_well",
    "market_stress_any"}, each 0, 1 or null. Applies SUSTAIN-HH-Risk-Rule v1.0
    (notebook section 12, variant A) and returns risk_class
    (Low/Medium/High/Unassigned), risk_ord, signal_count, unknown_count,
    reasons and rule_version. Rule-based; no ML model.

To use the database:  from app.core.database import get_supabase
"""

from typing import Any

from app.components.market_risk.ml import loader
from app.components.market_risk.ml.sustain_predict import validate_input
from app.components.market_risk.schemas import (
    FeatureInfo,
    Horizon,
    HorizonPrediction,
    IdentifyRequest,
    IdentifyResponse,
    MarketRiskFeatures,
    ModelInfoResponse,
    ModelSummary,
    PredictRequest,
    PredictResponse,
)

CATEGORY_FEATURE = "F_Category"

RULE_VERSION = "SUSTAIN-HH-Risk-Rule v1.0 (provisional, requires expert validation)"
RISK_CLASSES = ("Low", "Medium", "High")
# The three stress signals of rule variant A, with plain-English labels.
STRESS_SIGNALS = (
    ("no_profit_last_month", "No profit last month"),
    ("not_progressing_well", "Not progressing well"),
    ("market_stress_any", "Market stress"),
)
HIGH_SIGNAL_COUNT = 2


def get_status() -> dict:
    return {"component": "market_risk", "status": "ok"}


def _requested_horizons(horizon: str) -> tuple[str, ...]:
    return loader.HORIZONS if horizon == "both" else (horizon,)


def _convert_category(
    features: dict[str, Any], metadata: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Map upper-case survey category names to the trained levels."""
    value = features.get(CATEGORY_FEATURE)
    allowed = metadata["categorical_levels"].get(CATEGORY_FEATURE, [])
    if value is None or value in allowed:
        return features, []

    mapped = metadata.get("category_mapping", {}).get(str(value).strip().upper())
    if mapped is None:
        return features, []
    return (
        {**features, CATEGORY_FEATURE: mapped},
        [f"{CATEGORY_FEATURE}: converted {value!r} -> {mapped!r} using category_mapping"],
    )


def _missing_value_warnings(
    features: dict[str, Any], metadata: dict[str, Any]
) -> list[str]:
    warnings: list[str] = []
    null_numeric = [f for f in metadata["numeric_features"] if features.get(f) is None]
    if null_numeric:
        warnings.append(
            f"{len(null_numeric)} numeric features were null and will be "
            f"median-imputed: {', '.join(null_numeric)}"
        )
    for name in metadata["categorical_features"]:
        if features.get(name) is None:
            warnings.append(f"{name}: null -> encoded as all-zero")
    return warnings


def _predict_horizon(
    horizon: str, features: dict[str, Any]
) -> tuple[HorizonPrediction, list[str]]:
    import pandas as pd

    model, metadata = loader.load_model(horizon)
    features, warnings = _convert_category(features, metadata)
    warnings += _missing_value_warnings(features, metadata)

    row = pd.DataFrame([features], columns=metadata["feature_names_in_order"])
    X, issues = validate_input(row, metadata)
    warnings += issues

    proba = model.predict_proba(X)[0]
    labels = [metadata["classes"][int(c)] for c in model.classes_]
    probabilities = {label: round(float(p), 4) for label, p in zip(labels, proba)}
    status = loader.get_model_status(horizon)

    prediction = HorizonPrediction(
        horizon=horizon,
        model_name=metadata["model_name"],
        predicted_risk=labels[int(proba.argmax())],
        probabilities=probabilities,
        model_status=status["model_status"],
        deployment_reason=status["deployment_reason"],
    )
    return prediction, warnings


def predict_market_risk(request: PredictRequest | dict) -> PredictResponse:
    """Predict 3M and/or 6M household market risk from the 53 F_* features."""
    if not isinstance(request, PredictRequest):
        request = PredictRequest.model_validate(request)
    features = request.features.model_dump()

    predictions: list[HorizonPrediction] = []
    warnings: list[str] = []
    for horizon in _requested_horizons(request.horizon):
        prediction, horizon_warnings = _predict_horizon(horizon, features)
        predictions.append(prediction)
        warnings += [w for w in horizon_warnings if w not in warnings]

    return PredictResponse(
        horizon=request.horizon,
        predictions=predictions,
        warnings=warnings,
        placeholder=False,
    )


def get_model_info(horizon: Horizon | None = None) -> ModelInfoResponse:
    """Describe the models and their inputs without loading model.joblib."""
    horizons = loader.HORIZONS if horizon is None else (horizon,)

    models: list[ModelSummary] = []
    for h in horizons:
        metadata = loader.load_metadata(h)
        status = loader.get_model_status(h)
        known = {k: metadata[k] for k in ModelSummary.model_fields if k in metadata}
        models.append(ModelSummary(**{**known, "horizon": h, **status}))

    metadata = loader.load_metadata(horizons[0])
    # Prefer the clearer field descriptions in schemas.py over feature_schema.json.
    schema_fields = MarketRiskFeatures.model_fields
    features = []
    for item in loader.load_feature_schema(horizons[0]):
        field = schema_fields.get(item["name"])
        description = (field.description if field else None) or item["description"]
        features.append(
            FeatureInfo(name=item["name"], type=item["type"], description=description)
        )

    return ModelInfoResponse(
        models=models,
        features=features,
        categorical_levels=metadata["categorical_levels"],
    )


def _class_from_count(n_positive: int) -> int:
    if n_positive >= HIGH_SIGNAL_COUNT:
        return 2
    return 1 if n_positive >= 1 else 0


def identify_current_risk(request: IdentifyRequest | dict) -> IdentifyResponse:
    """Current risk class by SUSTAIN-HH-Risk-Rule v1.0 (notebook section 12, variant A).

    A class is assigned only if it is the same with blanks counted as 0 and as 1.
    Business not running -> High. Business status blank -> Unassigned unless the
    signals alone already give High (as in the notebook's risk_rule).
    """
    if not isinstance(request, IdentifyRequest):
        request = IdentifyRequest.model_validate(request)
    values = request.model_dump()
    business_not_running = values["business_not_running"]

    positive = [label for key, label in STRESS_SIGNALS if values[key] == 1]
    unknown = [label for key, label in STRESS_SIGNALS if values[key] is None]
    best_case = _class_from_count(len(positive))
    worst_case = _class_from_count(len(positive) + len(unknown))

    if business_not_running == 1:
        risk_ord, decision = 2, "Business not running -> High"
    elif best_case != worst_case:
        risk_ord, decision = None, "Blank answers could change the class -> Unassigned"
    elif business_not_running is None and best_case < 2:
        risk_ord, decision = None, "Business status not answered -> Unassigned"
    else:
        risk_ord = best_case
        decision = {
            0: "Business running and all three signals answered No -> Low",
            1: "Exactly one risk signal -> Medium",
            2: f"{HIGH_SIGNAL_COUNT} or more risk signals -> High",
        }[risk_ord]

    reasons: list[str] = []
    if business_not_running is None and not decision.startswith("Business status"):
        reasons.append("Business status not answered")
    reasons += positive
    reasons += [f"Not answered: {label.lower()}" for label in unknown]
    reasons.append(decision)

    return IdentifyResponse(
        risk_class="Unassigned" if risk_ord is None else RISK_CLASSES[risk_ord],
        risk_ord=risk_ord,
        signal_count=len(positive),
        unknown_count=len(unknown),
        reasons=reasons,
        rule_version=RULE_VERSION,
    )
