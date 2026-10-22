"""Build grounded SWOT output and its stored viability summary."""

from app.components.livelihood_planning.model_2_swot.factors import (
    get_livelihood_factors,
)
from app.components.livelihood_planning.model_2_swot.scoring import (
    PUBLIC_VIABILITY_FIELDS,
    get_viability,
    score_factors,
)
from app.components.livelihood_planning.model_2_swot.writer import (
    rewrite_factors,
    signal_strength,
)

SWOT_KEYS = ("strengths", "weaknesses", "opportunities", "threats")
SWOT_SINGULAR = {
    "strengths": "strength",
    "weaknesses": "weakness",
    "opportunities": "opportunity",
    "threats": "threat",
}
ESTIMATED_VIABILITY_NOTE = (
    "No district-level monitoring data for this livelihood and district; "
    "profitability and resilience use livelihood-level figures."
)


def build_swot(livelihood: str, features: dict) -> dict:
    """Return SWOT groups with the stable text/source public shape."""
    district = features.get("district")
    factors = get_livelihood_factors(livelihood, district)
    scored_factors = score_factors(factors, features)
    written_factors = rewrite_factors(scored_factors)
    result: dict[str, list[dict[str, str]]] = {key: [] for key in SWOT_KEYS}

    for factor in written_factors:
        category = str(factor.get("category", ""))
        if category in result:
            evidence_value = factor.get("evidence")
            evidence = str(
                evidence_value
                if evidence_value is not None
                else factor.get("text", "")
            )
            result[category].append(
                {
                    "text": str(factor.get("text", "")),
                    "source": str(factor.get("source") or ""),
                    "evidence": evidence,
                    "strength": signal_strength(evidence),
                }
            )

    return result


def build_swot_report(livelihood: str, features: dict) -> dict:
    """Return SWOT groups, viability, and Model 2 confidence warnings."""
    district_value = features.get("district")
    district = str(district_value).strip() if district_value else None
    viability_record = get_viability(livelihood, district)
    stored_confidence = float(viability_record.get("confidence", 0.0))
    estimated = bool(viability_record.get("estimated", True))
    viability = {
        field: viability_record[field] for field in PUBLIC_VIABILITY_FIELDS
    }
    viability["estimated"] = estimated

    notes: list[str] = []
    district_missing = district is None
    district_unknown = district is not None and estimated
    if district_missing:
        notes.append(
            "District was not provided, so district-specific monitoring is unavailable."
        )
    if district_unknown:
        notes.append(
            f"No district-level viability monitoring was found for {district}."
        )
    if estimated:
        notes.append(ESTIMATED_VIABILITY_NOTE)
        notes.append("The viability result is estimated.")
    if stored_confidence < 0.5:
        notes.append("Stored viability confidence is below 0.5.")

    swot_result = build_swot(livelihood, features)
    for category, singular in SWOT_SINGULAR.items():
        if not swot_result[category]:
            notes.append(
                f"No clear {singular} signal was found in the data for this "
                "livelihood and district."
            )

    is_low_confidence = (
        district_missing or district_unknown or estimated
    )
    return {
        "swot": swot_result,
        "viability": viability,
        "confidence": "low" if is_low_confidence else "normal",
        "notes": notes,
    }
