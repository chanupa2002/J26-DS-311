"""Rank SWOT facts and read stored livelihood viability scores."""

from statistics import fmean
from typing import Any

from app.core.database import get_supabase

SWOT_KEYS = ("strengths", "weaknesses", "opportunities", "threats")
VIABILITY_COLUMNS = (
    "livelihood,district,profitability,market,area,resilience,viability,"
    "viability_low,viability_high,confidence"
)
VIABILITY_FACT_COLUMNS = "is_estimated"
PUBLIC_VIABILITY_FIELDS = (
    "score",
    "low",
    "high",
    "profitability",
    "market",
    "area",
    "resilience",
)


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def score_factors(
    factors: list[dict[str, Any]], features: dict
) -> list[dict[str, Any]]:
    """Apply transparent ranking rules and keep the top three in each group."""
    _ = features
    grouped: dict[str, list[dict[str, Any]]] = {
        category: [] for category in SWOT_KEYS
    }
    for factor in factors:
        category = str(factor.get("category", ""))
        if category not in grouped:
            continue
        is_weak = "(weak signal)" in str(
            factor.get("text") or ""
        ).casefold()
        is_risk = str(factor.get("scope") or "").strip().casefold() == "risk"
        if category == "opportunities" and is_risk and is_weak:
            continue
        score = _number(factor.get("similarity"))
        if factor.get("district"):
            score += 0.1
        if bool(factor.get("is_estimated", False)):
            score -= 0.1
        if is_weak:
            score -= 0.2
        grouped[category].append({**factor, "score": score})

    selected: list[dict[str, Any]] = []
    for category in SWOT_KEYS:
        ranked = sorted(
            grouped[category],
            key=lambda factor: float(factor["score"]),
            reverse=True,
        )
        selected.extend(ranked[:3])
    return selected


def _empty_viability() -> dict[str, Any]:
    return {
        **{field: 0.0 for field in PUBLIC_VIABILITY_FIELDS},
        "confidence": 0.0,
        "estimated": True,
    }


def _viability_from_row(row: dict[str, Any], estimated: bool) -> dict[str, Any]:
    return {
        "score": _number(row.get("viability")),
        "low": _number(row.get("viability_low")),
        "high": _number(row.get("viability_high")),
        "profitability": _number(row.get("profitability")),
        "market": _number(row.get("market")),
        "area": _number(row.get("area")),
        "resilience": _number(row.get("resilience")),
        "confidence": _number(row.get("confidence")),
        "estimated": estimated,
    }


def _mean_viability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return _empty_viability()
    source_fields = {
        "score": "viability",
        "low": "viability_low",
        "high": "viability_high",
        "profitability": "profitability",
        "market": "market",
        "area": "area",
        "resilience": "resilience",
        "confidence": "confidence",
    }
    result = {
        output: fmean(_number(row.get(source)) for row in rows)
        for output, source in source_fields.items()
    }
    return {**result, "estimated": True}


def _viability_fact_is_estimated(
    client: Any, livelihood: str, district: str | None
) -> bool:
    """Read whether district viability evidence is itself estimated."""
    if not district:
        return True
    try:
        response = (
            client.table("livelihood_facts")
            .select(VIABILITY_FACT_COLUMNS)
            .eq("scope", "viability")
            .eq("livelihood", livelihood)
            .eq("district", district)
            .execute()
        )
        rows = response.data or []
    except Exception:
        return True
    if not rows or rows[0].get("is_estimated") is None:
        return True
    return bool(rows[0]["is_estimated"])


def get_viability(livelihood: str, district: str | None) -> dict[str, Any]:
    """Return a district score or an estimated cross-district mean."""
    try:
        client = get_supabase()
        response = (
            client.table("livelihood_scores")
            .select(VIABILITY_COLUMNS)
            .eq("livelihood", livelihood)
            .execute()
        )
        rows = response.data or []
    except Exception:
        return _empty_viability()

    cleaned_district = str(district).strip() if district else None
    if cleaned_district:
        for row in rows:
            row_district = str(row.get("district") or "").strip()
            if row_district.casefold() == cleaned_district.casefold():
                estimated = _viability_fact_is_estimated(
                    client, livelihood, cleaned_district
                )
                return _viability_from_row(row, estimated=estimated)
    result = _mean_viability(rows)
    if cleaned_district:
        result["estimated"] = _viability_fact_is_estimated(
            client, livelihood, cleaned_district
        )
    return result
