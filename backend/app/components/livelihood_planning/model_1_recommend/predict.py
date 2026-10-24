"""Inference helpers for the livelihood recommendation model."""

from typing import Any

from app.components.livelihood_planning.decision_trail import (
    build_recommendation_trail,
)
from app.components.livelihood_planning.model_1_recommend.loader import (
    AREA_COLUMNS,
    load_model,
)

# Tune these thresholds when the team recalibrates the close-score note.
LOW_CONFIDENCE_TOP_SCORE = 0.30
LOW_CONFIDENCE_GAP = 0.05
MIN_REASON_CONTRIBUTION = 0.02
MAX_REASONS = 3


def _format_reason(
    feature: str, value: object, standardized_value: float | None = None
) -> str:
    """Turn one contributing original feature into a readable reason."""
    if feature == "female_headed":
        return (
            "Female-headed household"
            if value == "Yes"
            else "Not a female-headed household"
        )
    if feature == "gender":
        return f"Gender: {value}"
    if feature == "disability":
        return (
            "Household member with a disability"
            if value == "Yes"
            else "No disability reported"
        )
    if feature == "aswesuma_category":
        return f"Aswesuma category: {value}"
    if feature == "age":
        numeric_age = float(value)
        display_age = int(numeric_age) if numeric_age.is_integer() else numeric_age
        return f"Age {display_age}"
    if feature == "district":
        return f"District: {value}"
    if feature == "ds_division":
        return f"DS division: {value}"

    area_labels = {
        "food_insecurity_score": "Area food insecurity",
        "debt_pct": "Area debt level",
        "land_pct": "Area land ownership",
    }
    if feature in area_labels:
        level = "high" if (standardized_value or 0.0) > 0 else "low"
        return f"{area_labels[feature]} is {level}"
    return f"{feature}: {value}"


def _clean_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    return cleaned if cleaned else None


def _clean_gender(value: object) -> object:
    cleaned = _clean_text(value)
    if isinstance(cleaned, str):
        normalized = cleaned.lower()
        if normalized in {"female", "male"}:
            return normalized.title()
    return None


def _clean_yes_no(value: object) -> object:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    cleaned = _clean_text(value)
    if isinstance(cleaned, str):
        normalized = cleaned.lower()
        if normalized in {"true", "yes"}:
            return "Yes"
        if normalized in {"false", "no"}:
            return "No"
    return None


def _is_missing_or_unknown(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or value.strip().casefold() == "unknown"
    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return False


def _original_feature_name(
    transformed_name: str, original_features: list[str]
) -> str | None:
    name_without_transformer = transformed_name.split("__", maxsplit=1)[-1]
    matches = [
        feature
        for feature in original_features
        if name_without_transformer == feature
        or name_without_transformer.startswith(f"{feature}_")
    ]
    return max(matches, key=len, default=None)


def _known_districts(preprocessor: Any) -> list[str]:
    categorical_pipeline = preprocessor.named_transformers_["cat"]
    encoder = categorical_pipeline.named_steps["onehot"]
    categorical_features = list(categorical_pipeline.feature_names_in_)
    district_index = categorical_features.index("district")
    return sorted(
        str(value)
        for value in encoder.categories_[district_index]
        if not _is_missing_or_unknown(value)
    )


def _district_values_after_imputation(
    preprocessor: Any, frame: Any, cleaned_values: dict[str, object]
) -> dict[str, object]:
    """Return the raw district values actually passed beyond imputation."""
    try:
        numeric_pipeline = preprocessor.named_transformers_["num"]
        numeric_features = list(numeric_pipeline.feature_names_in_)
        imputer = numeric_pipeline.named_steps["imputer"]
        imputed = imputer.transform(frame[numeric_features])[0]
        values = dict(zip(numeric_features, imputed, strict=True))
    except (AttributeError, KeyError, TypeError, ValueError):
        values = cleaned_values
    return {column: values.get(column) for column in AREA_COLUMNS}


def _recommendation_reasons(
    class_index: int,
    classifier: Any,
    transformed_names: list[str],
    transformed_row: Any,
    original_features: list[str],
    cleaned_values: dict[str, object],
) -> list[str]:
    contributions = classifier.coef_[class_index] * transformed_row
    grouped: dict[str, float] = {}
    standardized_values: dict[str, float] = {}

    for position, transformed_name in enumerate(transformed_names):
        original = _original_feature_name(transformed_name, original_features)
        if original is None:
            continue
        grouped[original] = grouped.get(original, 0.0) + float(
            contributions[position]
        )
        if transformed_name.startswith("num__"):
            standardized_values[original] = float(transformed_row[position])

    ranked_features = sorted(
        (
            (feature, contribution)
            for feature, contribution in grouped.items()
            if contribution > MIN_REASON_CONTRIBUTION
            and not _is_missing_or_unknown(cleaned_values.get(feature))
        ),
        key=lambda item: item[1],
        reverse=True,
    )[:MAX_REASONS]
    return [
        _format_reason(
            feature,
            cleaned_values[feature],
            standardized_values.get(feature),
        )
        for feature, _ in ranked_features
    ]


def recommend_with_context(features: dict, k: int = 3) -> dict:
    """Return ranked recommendations plus explanation and confidence context."""
    import numpy as np
    import pandas as pd

    model, info, area_index = load_model()
    feature_names = list(info["features"])

    district = _clean_text(features.get("district"))
    area_key = district.lower() if isinstance(district, str) else None
    area_found = area_key in area_index if area_key is not None else False
    area_values = area_index.get(area_key, {}) if area_key is not None else {}

    age = features.get("age")
    if isinstance(age, bool):
        age = np.nan
    else:
        age = pd.to_numeric(age, errors="coerce")

    cleaned_values = {
        "district": district,
        "ds_division": _clean_text(features.get("ds_division")),
        "gender": _clean_gender(features.get("gender")),
        "female_headed": _clean_yes_no(features.get("female_headed")),
        "disability": _clean_yes_no(features.get("disability")),
        "aswesuma_category": _clean_text(
            features.get("aswesuma_category")
        ),
        "age": age,
        **{column: area_values.get(column, np.nan) for column in AREA_COLUMNS},
    }
    row = [
        cleaned_values.get(name, _clean_text(features.get(name)))
        for name in feature_names
    ]
    row = [np.nan if value is None else value for value in row]
    frame = pd.DataFrame([row], columns=feature_names)

    probabilities = np.asarray(model.predict_proba(frame)[0], dtype=float)
    classes = np.asarray(getattr(model, "classes_", info["classes"]))
    preprocessor = model.named_steps["prep"]
    classifier = model.named_steps["model"]
    transformed = preprocessor.transform(frame)
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()
    transformed_row = np.asarray(transformed, dtype=float)[0]
    transformed_names = [
        str(name) for name in preprocessor.get_feature_names_out()
    ]
    standardized_area_values = {
        column: float(transformed_row[transformed_names.index(f"num__{column}")])
        for column in AREA_COLUMNS
        if f"num__{column}" in transformed_names
    }
    district_values = _district_values_after_imputation(
        preprocessor, frame, cleaned_values
    )

    limit = max(0, min(k, len(classes)))
    top_indices = np.argsort(-probabilities, kind="stable")[:limit]
    recommendations = [
        {
            "livelihood": str(classes[index]),
            "score": round(float(probabilities[index]), 4),
            "reasons": _recommendation_reasons(
                int(index),
                classifier,
                transformed_names,
                transformed_row,
                feature_names,
                cleaned_values,
            ),
        }
        for index in top_indices
    ]

    notes: list[str] = []
    sorted_probabilities = np.sort(probabilities)[::-1]
    top_score = float(sorted_probabilities[0])
    top_gap = (
        float(sorted_probabilities[0] - sorted_probabilities[1])
        if len(sorted_probabilities) > 1
        else 1.0
    )
    low_top_score = top_score < LOW_CONFIDENCE_TOP_SCORE
    close_gap = top_gap < LOW_CONFIDENCE_GAP
    if low_top_score or close_gap:
        notes.append("The top suggestions are close in score; review them carefully.")

    known_districts = _known_districts(preprocessor)
    district_is_trained = isinstance(district, str) and district.casefold() in {
        known.casefold() for known in known_districts
    }
    if not district_is_trained:
        district_name = (
            district if isinstance(district, str) else "this district"
        )
        notes.append(
            f"Low confidence for {district_name}. Results are general "
            "suggestions; review carefully."
        )

    confidence = "normal" if district_is_trained else "low"
    recommendation_trail = build_recommendation_trail(
        cleaned_values=cleaned_values,
        district_values=district_values,
        area_found=area_found,
        classes=[str(value) for value in classes],
        probabilities=[float(value) for value in probabilities],
        recommendations=recommendations,
        confidence=confidence,
        district_is_trained=district_is_trained,
        known_districts=known_districts,
        close_gap=close_gap,
        low_top_score=low_top_score,
        standardized_area_values=standardized_area_values,
    )

    return {
        "recommendations": recommendations,
        "confidence": confidence,
        "notes": notes,
        "decision_trail": {
            "version": 1,
            "recommendation": recommendation_trail,
        },
    }


def recommend_top_k(features: dict, k: int = 3) -> list[dict]:
    """Return the highest-probability livelihood categories."""
    return recommend_with_context(features, k)["recommendations"]
