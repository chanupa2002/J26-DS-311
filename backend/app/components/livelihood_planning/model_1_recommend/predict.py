"""Inference helpers for the livelihood recommendation model."""

from typing import Any

from app.components.livelihood_planning.model_1_recommend.loader import (
    AREA_COLUMNS,
    load_model,
)

# Tune these two thresholds when the team recalibrates confidence on new data.
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
    area_values = (
        area_index.get(district.lower(), {})
        if isinstance(district, str)
        else {}
    )

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
    if top_score < LOW_CONFIDENCE_TOP_SCORE or top_gap < LOW_CONFIDENCE_GAP:
        notes.append("Low confidence: the top suggestions are close together.")

    known_districts = _known_districts(preprocessor)
    if isinstance(district, str) and district.casefold() not in {
        known.casefold() for known in known_districts
    }:
        known_district_list = ", ".join(known_districts)
        notes.append(
            "This district was not in the training data "
            f"({known_district_list}); results are less reliable."
        )

    return {
        "recommendations": recommendations,
        "confidence": "low" if notes else "normal",
        "notes": notes,
    }


def recommend_top_k(features: dict, k: int = 3) -> list[dict]:
    """Return the highest-probability livelihood categories."""
    return recommend_with_context(features, k)["recommendations"]
