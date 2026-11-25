"""v2 use cases: connect the artifacts, the pure pipeline and the CSV visit store.

The store holds synthetic households only. Real visits are scored from the request
and are never stored, listed or logged.
"""

import threading
from typing import Any

import pandas as pd

from app.components.market_risk.v2 import artifacts, pipeline
from app.components.market_risk.v2.schemas import VisitRequest

RULE_VERSION = "SUSTAIN-HH-Risk-Rule v1.0 (provisional, requires expert validation)"
REAL_VISIT_NOTE = "indicative - no history"
SYNTHETIC_NOTE = "Simulated household data."
MARKET_NOTE = "Public market indicators; no household data."
EVIDENCE_NOTE = "Outcome labels come from simulated households only."

_shap_lock = threading.Lock()

# (name, sheet, metric, model row, persistence row); None = the chosen model's row.
COMPARISONS = (
    ("3M warning, single test month", "Test_3M_EarlyWarning", "ROC_AUC", None,
     "Baseline: current risk level (persistence)"),
    ("3M warning, rolling origin", "Rolling_Origin_3M_Pooled", "ROC_AUC",
     "Early warning - model (pooled)", "Early warning - persistence (pooled)"),
    ("3M classes, single test month", "Test_3M_Classes", "balanced_accuracy", None,
     "Baseline: risk stays the same"),
    ("3M classes, rolling origin", "Rolling_Origin_3M_Pooled", "balanced_accuracy",
     "3 classes - model (pooled)", "3 classes - persistence (pooled)"),
    ("6M warning, grouped CV", "Results_6M_GroupCV", "ROC_AUC",
     "Early warning - model", "Early warning - persistence"),
    ("6M classes, grouped CV", "Results_6M_GroupCV", "balanced_accuracy",
     "3 classes - model", "3 classes - persistence"),
)
RELIABILITY_CHECKS = {"3M": "3M warning, rolling origin", "6M": "6M warning, grouped CV"}


class MarketDataUnavailable(RuntimeError):
    """The month is outside the market data. The message is safe to show."""


class UnknownValue(ValueError):
    """A district or category that the market table does not know."""


class HouseholdNotFound(LookupError):
    pass


def _number(value) -> float | None:
    return None if pd.isna(value) else float(value)


def _text(value) -> str | None:
    return None if pd.isna(value) else str(value)


def _alert(value) -> bool | None:
    return None if value is None or pd.isna(value) else bool(value)


def _check_month(bundle: artifacts.Bundle, month: str) -> None:
    if month not in bundle.months:
        raise MarketDataUnavailable(
            f"No market data for {month}. Data covers {bundle.months[0]} to {bundle.months[-1]}; "
            "a monthly market-data update is planned."
        )


def _comparison_rows(bundle: artifacts.Bundle) -> list[dict[str, Any]]:
    sheets = bundle.evidence["sheets"]
    chosen = {
        "Test_3M_EarlyWarning": bundle.meta["warning_model"],
        "Test_3M_Classes": bundle.meta["classes_model"],
    }
    rows = []
    for name, sheet, metric, model_row, baseline_row in COMPARISONS:
        if model_row is None:
            model_row = f"{chosen[sheet]['model']} [{chosen[sheet]['features']}] (chosen)"
        by_model = {row["model"]: row for row in sheets[sheet]}
        model, persistence = float(by_model[model_row][metric]), float(by_model[baseline_row][metric])
        rows.append({
            "name": name, "metric": metric, "model": model,
            "persistence": persistence, "model_better": model > persistence,
        })
    return rows


def _reliability_notes(bundle: artifacts.Bundle) -> dict[str, str | None]:
    by_name = {row["name"]: row for row in _comparison_rows(bundle)}
    notes: dict[str, str | None] = {}
    for horizon, name in RELIABILITY_CHECKS.items():
        row = by_name[name]
        notes[horizon] = None if row["model_better"] else (
            f"Indicative only: in testing this {horizon} model did not beat assuming risk stays the same."
        )
    return notes


def _current_risk(row: pd.Series) -> dict[str, Any]:
    return {
        "risk_class": row.risk_class_t,
        "risk_ord": None if pd.isna(row.risk_ord_t) else int(row.risk_ord_t),
        "signal_count": int(row.risk_signals_t),
        "reasons": pipeline.reasons(row),
        "rule_version": RULE_VERSION,
    }


def _grant_status(value: Any) -> dict[str, Any]:
    """Grant status code and its codebook label (the same mapping as the SHAP factor values)."""
    if value is None or pd.isna(value):
        return {"grant_status": None, "grant_status_label": None}
    code = int(value)
    return {"grant_status": code, "grant_status_label": pipeline.CODED_VALUES["grant_status"].get(code)}


def _visit_warnings(bundle: artifacts.Bundle, row: pd.Series) -> list[str]:
    warnings = []
    if row.district not in bundle.training_districts:
        warnings.append(f"{row.district} was not among the districts used for training.")
    if row.category in pipeline.FALLBACK_MARKET_CATEGORY:
        warnings.append("Category is UNASSIGNED: the general consumer-price series is used for market pressure.")
    if pd.isna(row.market_pressure):
        warnings.append("No market pressure value for this district, category and month.")
    if pd.isna(row.revenue_low) and pd.notna(row.revenue_band):
        warnings.append("No poverty line is published for this month or earlier.")
    return warnings


def _visit_payload(bundle: artifacts.Bundle, features: pd.DataFrame, predictions: pd.DataFrame,
                   household_key: str | None, is_synthetic: bool, note: str | None) -> dict[str, Any]:
    """Build the response for the single visit in `features`."""
    row, predicted = features.iloc[0], predictions.iloc[0]
    columns = bundle.meta["feature_columns"][bundle.meta["warning_model"]["features"]]
    with _shap_lock:
        base, factors = pipeline.shap_top_factors(
            bundle.models["3M_warning"], bundle.explainer_3m, pipeline.design(features, columns),
            row, bundle.revenue_labels,
        )
    reliability = _reliability_notes(bundle)
    return {
        "is_synthetic": is_synthetic,
        "model_version": "v2",
        "note": note,
        "household_key": household_key,
        "monitoring_period": row.monitoring_period,
        "district": row.district,
        "category": row.category,
        **_grant_status(row.grant_status),
        "current_risk": _current_risk(row),
        "predictions": {
            "1M": bundle.transitions.next_month(row.risk_class_t),
            **{horizon: {
                "p_high": float(predicted[f"P_High_{horizon}"]),
                "predicted_class": predicted[f"predicted_{horizon}"],
                "alert": _alert(predicted[f"high_alert_{horizon}"]),
                "alert_threshold": bundle.meta["high_alert_threshold"][horizon],
                "reliability_note": reliability[horizon],
            }
            for horizon in pipeline.HORIZONS},
        },
        "shap_base_value": base,
        "shap_top_factors": factors,
        "market": {
            "pressure": _number(row.market_pressure),
            "level": _text(row.market_pressure_level),
            "price_month_used": _text(row.market_price_month_used),
            "series": _text(row.market_series),
            "basis": _text(row.market_ipa_basis),
        },
        "warnings": _visit_warnings(bundle, row),
    }


def _earlier_visits(bundle: artifacts.Bundle, request: VisitRequest) -> pd.DataFrame:
    identity = {
        "household_key": request.household_key, "is_synthetic": request.is_synthetic,
        "district": request.district, "category": request.category,
    }
    if request.previous_visits is not None:
        return pd.DataFrame([{**identity, **visit.model_dump()} for visit in request.previous_visits])
    if request.household_key is None:
        return pd.DataFrame()
    store = bundle.store_visits
    return store[
        (store.household_key == request.household_key)
        & (store.monitoring_period < request.monitoring_period)
    ]


def score_visit(request: VisitRequest) -> dict[str, Any]:
    bundle = artifacts.load_bundle()
    _check_month(bundle, request.monitoring_period)
    if request.district not in bundle.districts:
        raise UnknownValue("Unknown district.")
    if request.category not in {*bundle.categories, *pipeline.FALLBACK_MARKET_CATEGORY}:
        raise UnknownValue("Unknown category.")

    current = pd.DataFrame([request.model_dump(exclude={"previous_visits"})])
    earlier = _earlier_visits(bundle, request)
    records = [
        record
        for frame in (earlier, current)
        for record in frame.reindex(columns=pipeline.VISIT_INPUT_COLUMNS).to_dict("records")
    ]
    visits = pd.DataFrame(records, columns=pipeline.VISIT_INPUT_COLUMNS)
    features = pipeline.build_features(visits, bundle.tables).iloc[[-1]]
    predictions = pipeline.predict_visits(features, bundle.models, bundle.meta)
    note = None if request.is_synthetic else REAL_VISIT_NOTE
    return _visit_payload(bundle, features, predictions, request.household_key, request.is_synthetic, note)


def _stored(bundle: artifacts.Bundle) -> pd.DataFrame:
    return bundle.store_features.join(bundle.store_predictions)


def list_households(month: str | None) -> dict[str, Any]:
    bundle = artifacts.load_bundle()
    month = month or bundle.months[-1]
    _check_month(bundle, month)
    rows = _stored(bundle)
    rows = rows[rows.monitoring_period == month].sort_values("household_key")
    households = [
        {
            "household_key": str(row.household_key),
            "monitoring_period": row.monitoring_period,
            "district": row.district,
            "category": row.category,
            "is_synthetic": True,
            **_grant_status(row.grant_status),
            "current_risk": row.risk_class_t,
            "reasons": pipeline.reasons(row),
            **bundle.transitions.row_summary(row.risk_class_t),
            "predicted_3m": row.predicted_3M,
            "p_high_3m": float(row.P_High_3M),
            "alert_3m": _alert(row.high_alert_3M),
            "market_level": _text(row.market_pressure_level),
        }
        for row in rows.itertuples()
    ]
    return {
        "is_synthetic": True, "model_version": "v2", "note": SYNTHETIC_NOTE,
        "month": month, "count": len(households), "households": households,
    }


def household_detail(household_key: str) -> dict[str, Any]:
    bundle = artifacts.load_bundle()
    mask = bundle.store_features.household_key == household_key
    if not mask.any():
        raise HouseholdNotFound(household_key)
    features = bundle.store_features[mask].sort_values("month_index")
    predictions = bundle.store_predictions.loc[features.index]
    timeline = [
        {
            "monitoring_period": row.monitoring_period,
            "current_risk": row.risk_class_t,
            "reasons": pipeline.reasons(row),
            **bundle.transitions.row_summary(row.risk_class_t),
            "predicted_3m": predicted.predicted_3M,
            "p_high_3m": float(predicted.P_High_3M),
            "alert_3m": _alert(predicted.high_alert_3M),
            "market_level": _text(row.market_pressure_level),
        }
        for (_, row), (_, predicted) in zip(features.iterrows(), predictions.iterrows())
    ]
    latest = _visit_payload(
        bundle, features.iloc[[-1]], predictions.iloc[[-1]], household_key, True, SYNTHETIC_NOTE
    )
    return {
        "is_synthetic": True, "model_version": "v2", "note": SYNTHETIC_NOTE,
        "household_key": household_key, "latest_visit": latest, "timeline": timeline,
    }


def market_table(month: str | None) -> dict[str, Any]:
    bundle = artifacts.load_bundle()
    month = month or bundle.months[-1]
    _check_month(bundle, month)
    table = bundle.tables.market
    table = table[table.month == month].sort_values(["district", "category"])
    rows = [
        {
            "district": row.district,
            "category": row.category,
            "market_pressure": _number(row.market_pressure),
            "market_pressure_level": _text(row.market_pressure_level),
            "price_month_used": _text(row.price_month_used),
            "series": _text(row.series),
            "ipa_basis": _text(row.ipa_basis),
            "dmc_affected_families": _number(row.dmc_affected_families),
        }
        for row in table.itertuples()
    ]
    return {
        "is_synthetic": False, "model_version": "v2", "note": MARKET_NOTE,
        "month": month, "available_months": bundle.months, "count": len(rows), "rows": rows,
    }


def model_evidence() -> dict[str, Any]:
    bundle = artifacts.load_bundle()
    sheets = bundle.evidence["sheets"]
    comparisons = _comparison_rows(bundle)
    behind = [row["name"] for row in comparisons if not row["model_better"]]
    limitations = [
        "Outcome labels exist only for simulated households, so these results are not real-world validation.",
        f"Models were trained on {len(bundle.training_districts)} districts; other districts are outside the training data.",
        "6M results are indicative: too few months were available for a time-separated test.",
        "No 6M alert is issued because no reliable threshold could be set."
        if bundle.meta["high_alert_threshold"]["6M"] is None else "A 6M alert threshold is set.",
        f"Market data covers {bundle.months[0]} to {bundle.months[-1]}; later months return 503.",
        "The current-risk rule is provisional and needs expert validation.",
        "SHAP shows what drives the model, not real-world causes.",
    ]
    if behind:
        limitations.insert(0, "The model did not beat assuming risk stays the same in: " + "; ".join(behind) + ".")
    return {
        "is_synthetic": True, "model_version": "v2", "note": EVIDENCE_NOTE,
        "models": {"warning": bundle.meta["warning_model"], "classes": bundle.meta["classes_model"]},
        "alert_thresholds": bundle.meta["high_alert_threshold"],
        "comparisons": comparisons,
        "results": {
            name: sheets[name]
            for name in ("Test_3M_Classes", "Test_3M_EarlyWarning", "Rolling_Origin_3M",
                         "Rolling_Origin_3M_Pooled", "Results_6M_GroupCV")
        },
        "shap_group_share": sheets["SHAP_Groups_3M"],
        "threshold_register": sheets["Threshold_Register"],
        "transitions": bundle.transitions.evidence(),
        "limitations": limitations,
    }
