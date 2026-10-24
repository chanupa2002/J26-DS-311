"""Build plain-language decision trails from request-time model values."""

from enum import Enum
from typing import Any


class TrailFlag(str, Enum):
    OK = "ok"
    NOTE = "note"
    WARNING = "warning"


FORM_FIELDS = (
    "district",
    "ds_division",
    "age",
    "gender",
    "female_headed",
    "disability",
    "aswesuma_category",
)


def _clean_value(value: object) -> object:
    try:
        if value != value:
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return value.item()
    return value


def _step(
    step_id: str,
    title: str,
    summary: str,
    flag: TrailFlag,
    details: dict[str, Any],
) -> dict[str, Any]:
    words = summary.split()
    if len(words) > 25:
        summary = f"{' '.join(words[:24]).rstrip('.,;:')}…"
    return {
        "id": step_id,
        "title": title,
        "summary": summary,
        "flag": flag.value,
        "details": details,
    }


def format_livelihood_name(value: str) -> str:
    return value.strip().lower().title()


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    return singular if count == 1 else (plural or f"{singular}s")


def _was_were(count: int) -> str:
    return "was" if count == 1 else "were"


def _is_are(count: int) -> str:
    return "is" if count == 1 else "are"


def _plain_reason(
    reason: str,
    livelihood: str,
    standardized_area_values: dict[str, float],
) -> str:
    name = format_livelihood_name(livelihood)
    exact = {
        "Female-headed household": (
            f"A female-headed household raised the score for {name}."
        ),
        "Not a female-headed household": (
            f"Not being a female-headed household raised the score for {name}."
        ),
        "Household member with a disability": (
            f"A reported disability raised the score for {name}."
        ),
        "No disability reported": (
            f"No reported disability raised the score for {name}."
        ),
    }
    if reason in exact:
        return exact[reason]
    if reason.startswith("Gender: "):
        value = reason.removeprefix("Gender: ").lower()
        return f"Being {value} raised the score for {name}."
    if reason.startswith("Aswesuma category: "):
        value = reason.removeprefix("Aswesuma category: ")
        return f"The {value} Aswesuma category raised the score for {name}."
    if reason.startswith("Age "):
        return f"{reason} raised the score for {name}."
    if reason.startswith("District: "):
        value = reason.removeprefix("District: ")
        return f"Living in {value} raised the score for {name}."
    if reason.startswith("DS division: "):
        value = reason.removeprefix("DS division: ")
        return f"Living in {value} DS division raised the score for {name}."
    area_reasons = {
        "Area food insecurity": (
            "food_insecurity_score",
            "Food worry in this district",
        ),
        "Area debt level": ("debt_pct", "Debt in this district"),
        "Area land ownership": ("land_pct", "Land ownership in this district"),
    }
    for prefix, (feature, label) in area_reasons.items():
        if reason.startswith(prefix):
            direction = "above" if reason.endswith("high") else "below"
            standardized = standardized_area_values.get(feature)
            qualifier = (
                ""
                if standardized is not None and abs(standardized) > 1
                else "slightly "
            )
            return (
                f"{label} is {qualifier}{direction} the usual level; "
                f"this raised the score for {name}."
            )
    return f"{reason} raised the score for {name}."


def build_recommendation_trail(
    *,
    cleaned_values: dict[str, object],
    district_values: dict[str, object],
    area_found: bool,
    classes: list[str],
    probabilities: list[float],
    recommendations: list[dict[str, Any]],
    confidence: str,
    district_is_trained: bool,
    known_districts: list[str],
    close_gap: bool,
    low_top_score: bool,
    standardized_area_values: dict[str, float],
) -> dict[str, Any]:
    """Build Model 1 steps without changing recommendation values."""
    district = _clean_value(cleaned_values.get("district"))
    form_details = {
        field: _clean_value(cleaned_values.get(field)) for field in FORM_FIELDS
    }
    area_details = {
        "food_worry_score": _clean_value(
            district_values.get("food_insecurity_score")
        ),
        "debt_percent": _clean_value(district_values.get("debt_pct")),
        "land_percent": _clean_value(district_values.get("land_pct")),
    }
    if area_found:
        input_summary = f"Household details and area values for {district} were used."
    elif district:
        input_summary = (
            "The household details were used. "
            f"No area record was found for {district}, so typical district values were used."
        )
    else:
        input_summary = (
            "The household details were used. "
            "No district was provided, so typical district values were used."
        )

    ranked_scores = sorted(
        zip(classes, probabilities, strict=True),
        key=lambda item: item[1],
        reverse=True,
    )
    scores = [
        {
            "rank": rank,
            "livelihood": format_livelihood_name(livelihood),
            "percentage": round(float(probability) * 100, 4),
            "top_three": rank <= 3,
        }
        for rank, (livelihood, probability) in enumerate(ranked_scores, 1)
    ]
    highest = scores[0]["livelihood"] if scores else "No option"

    top_three = [
        {
            "rank": rank,
            "livelihood": format_livelihood_name(str(item["livelihood"])),
            "percentage": round(float(item["score"]) * 100, 2),
            "reasons": [
                _plain_reason(
                    reason,
                    str(item["livelihood"]),
                    standardized_area_values,
                )
                for reason in item.get("reasons", [])
            ],
        }
        for rank, item in enumerate(recommendations, 1)
    ]

    confidence_reasons: list[str] = []
    if not district_is_trained:
        if district:
            confidence_reasons.append(
                "This district is outside the areas the model learned from."
            )
        else:
            confidence_reasons.append("No district was provided.")
    if close_gap:
        confidence_reasons.append("The two leading options were almost equal.")
    elif low_top_score:
        confidence_reasons.append("No option had a strong leading score.")

    if confidence == "low":
        if district:
            confidence_summary = (
                "The household details support these suggestions. "
                "Needs a local check because this district is outside the areas "
                "the model learned from."
            )
        else:
            confidence_summary = (
                "The household details support these suggestions. "
                "Needs a local check because no district was provided."
            )
        confidence_flag = TrailFlag.WARNING
    elif close_gap:
        confidence_summary = (
            "The model learned from this district. "
            "The leading options were almost equal."
        )
        confidence_flag = TrailFlag.NOTE
    elif low_top_score:
        confidence_summary = (
            "This district is within the areas the model learned from. "
            "No option had a strong leading score."
        )
        confidence_flag = TrailFlag.NOTE
    else:
        confidence_summary = (
            "The district was covered and one option had a clear lead."
        )
        confidence_flag = TrailFlag.OK

    return {
        "steps": [
            _step(
                "recommendation-inputs",
                "What we looked at",
                input_summary,
                TrailFlag.OK if area_found else TrailFlag.WARNING,
                {
                    "form_details": form_details,
                    "district_values": area_details,
                    "area_record_found": area_found,
                    "used_typical_district_values": not area_found,
                },
            ),
            _step(
                "recommendation-scoring",
                "How we scored the options",
                f"{len(scores)} {_plural(len(scores), 'livelihood option')} "
                f"{_was_were(len(scores))} compared; {highest} scored highest.",
                TrailFlag.OK,
                {"scores": scores, "percentage_total": round(sum(item["percentage"] for item in scores), 4)},
            ),
            _step(
                "recommendation-top3",
                "Why these three",
                "The three highest scores were kept, with model reasons shown for each.",
                TrailFlag.OK,
                {"recommendations": top_three},
            ),
            _step(
                "recommendation-confidence",
                "How sure we are",
                confidence_summary,
                confidence_flag,
                {
                    "level": confidence,
                    "district": district,
                    "district_in_training": district_is_trained,
                    "training_districts": known_districts,
                    "close_top_scores": close_gap,
                    "low_top_score": low_top_score,
                    "reasons": confidence_reasons,
                },
            ),
        ]
    }


def build_swot_trail(
    *,
    livelihood: str,
    district: str | None,
    factors: list[dict[str, Any]],
    selected_factors: list[dict[str, Any]],
    written_factors: list[dict[str, Any]],
    viability_record: dict[str, Any],
    confidence: str,
    district_missing: bool,
    district_unknown: bool,
) -> dict[str, Any]:
    """Build Model 2 steps from retrieved, ranked, and checked values."""
    local_count = sum(bool(factor.get("district")) for factor in factors)
    estimated_count = sum(
        bool(factor.get("is_estimated", False)) for factor in factors
    )
    request_district = district or "no district"
    display_livelihood = format_livelihood_name(livelihood)
    fact_count = len(factors)
    if fact_count:
        facts_summary = (
            f"{local_count} of {fact_count} {_plural(fact_count, 'fact')} "
            f"{_is_are(local_count)} from this district."
        )
        if local_count < fact_count:
            facts_summary += " The rest come from wider district data."
    else:
        facts_summary = "No facts were found for this livelihood and district."

    group_ranks: dict[str, int] = {}
    selection = []
    for factor in selected_factors:
        group = str(factor.get("category") or "")
        group_ranks[group] = group_ranks.get(group, 0) + 1
        match_score = _clean_value(factor.get("similarity"))
        if match_score is not None:
            chosen_because = "Closest match by meaning"
        elif factor.get("district"):
            chosen_because = "Describes this district"
        else:
            chosen_because = "Describes the wider area"
        selection.append(
            {
                "group": group,
                "rank": group_ranks[group],
                "fact": str(factor.get("text") or ""),
                "match_score": match_score,
                "ranking_score": _clean_value(factor.get("score")),
                "chosen_because": chosen_because,
                "district_specific": bool(factor.get("district")),
                "estimated": bool(factor.get("is_estimated", False)),
                "weak": "(weak signal)" in str(factor.get("text") or "").casefold(),
                "source": str(factor.get("source") or ""),
                "records": _clean_value(factor.get("n_obs")),
            }
        )

    matched_count = sum(
        point["match_score"] is not None for point in selection
    )
    point_count = len(selection)
    if point_count and matched_count == point_count:
        selection_summary = (
            "Points were chosen by how closely they match this livelihood and "
            "district; local evidence was preferred."
        )
    elif matched_count:
        selection_summary = (
            f"{matched_count} of {point_count} {_plural(point_count, 'point')} "
            f"{_was_were(matched_count)} matched by meaning; the rest were "
            "chosen because they describe this district or the wider area."
        )
    else:
        selection_summary = (
            "Points were chosen because they describe this livelihood in this "
            "district or the wider area."
        )

    wording = [
        {
            "group": str(factor.get("category") or ""),
            "sentence": str(factor.get("text") or ""),
            "original_fact": str(factor.get("evidence") or ""),
            "wording": (
                "reworded"
                if bool(factor.get("_decision_was_reworded", False))
                else "original"
            ),
            "number_check_passed": bool(
                factor.get("_decision_number_check_passed", True)
            ),
            "source": str(factor.get("source") or ""),
            "records": _clean_value(factor.get("n_obs")),
        }
        for factor in written_factors
    ]
    reworded_count = sum(item["wording"] == "reworded" for item in wording)
    original_count = len(wording) - reworded_count
    sentence_count = len(wording)
    source_fact_phrase = (
        "its source fact" if sentence_count == 1 else "their source facts"
    )
    wording_summary = (
        f"{sentence_count} {_plural(sentence_count, 'sentence')} "
        f"{_was_were(sentence_count)} checked against {source_fact_phrase}. "
        f"{reworded_count} {_plural(reworded_count, 'sentence')} "
        f"{_was_were(reworded_count)} reworded; {original_count} "
        f"{_plural(original_count, 'sentence')} kept the original wording."
    )

    points_show_sources_and_records = bool(written_factors) and all(
        str(factor.get("source") or "").strip()
        and factor.get("n_obs") is not None
        for factor in written_factors
    )

    estimated = bool(viability_record.get("estimated", True))
    viability_details = {
        "parts": {
            name: _clean_value(viability_record.get(name))
            for name in ("profitability", "market", "area", "resilience")
        },
        "overall_score": _clean_value(viability_record.get("score")),
        "range": {
            "low": _clean_value(viability_record.get("low")),
            "high": _clean_value(viability_record.get("high")),
        },
        "rank_stability": _clean_value(viability_record.get("confidence")),
        "estimated": estimated,
    }
    if estimated:
        viability_summary = (
            "The viability result is based on wider district evidence. "
            "Not enough records came from this exact district."
        )
    else:
        viability_summary = (
            f"The overall viability score was {_clean_value(viability_record.get('score'))} out of 100."
        )

    confidence_reasons: list[str] = []
    if district_missing:
        confidence_reasons.append("No district was provided.")
    if district_unknown:
        confidence_reasons.append(
            "Not enough records were available from this exact district."
        )
    if estimated:
        confidence_reasons.append(
            "Not enough exact-district records were available, so wider district evidence was used."
        )
    stored_confidence = float(viability_record.get("confidence", 0.0))
    if stored_confidence < 0.5:
        confidence_reasons.append("The stored rank stability was below 0.5.")

    if confidence == "low":
        if district_missing:
            confidence_summary = (
                "Evidence supports a starting point. "
                "Needs a local check because no district was provided."
            )
        else:
            confidence_summary = (
                "Evidence supports this result. Needs a local check because "
                "exact-district records are limited."
            )
        confidence_flag = TrailFlag.WARNING
    elif stored_confidence < 0.5:
        confidence_summary = (
            "Evidence supports this result. Rank stability is below 0.5."
        )
        confidence_flag = TrailFlag.NOTE
    else:
        confidence_summary = "Local evidence supports this result."
        confidence_flag = TrailFlag.OK
    if points_show_sources_and_records:
        confidence_summary += (
            " Every point shows its source and the supporting record count."
        )

    return {
        "steps": [
            _step(
                "swot-request",
                "What we asked",
                f"Model 1 selected {display_livelihood} for {request_district}, and Model 2 reviewed that option.",
                TrailFlag.OK,
                {"livelihood": display_livelihood, "district": district},
            ),
            _step(
                "swot-facts",
                "What evidence we found",
                facts_summary,
                TrailFlag.NOTE if estimated_count else TrailFlag.OK,
                {
                    "facts_found": len(factors),
                    "district_facts": local_count,
                    "estimated_facts": estimated_count,
                },
            ),
            _step(
                "swot-selection",
                "Why these points",
                selection_summary,
                TrailFlag.OK,
                {"points": selection},
            ),
            _step(
                "swot-wording",
                "How the sentences were checked",
                wording_summary,
                TrailFlag.NOTE if original_count else TrailFlag.OK,
                {
                    "reworded_count": reworded_count,
                    "original_count": original_count,
                    "points": wording,
                },
            ),
            _step(
                "swot-viability",
                "How workable it looks",
                viability_summary,
                TrailFlag.NOTE if estimated else TrailFlag.OK,
                viability_details,
            ),
            _step(
                "swot-confidence",
                "How sure we are",
                confidence_summary,
                confidence_flag,
                {
                    "level": confidence,
                    "reasons": confidence_reasons,
                    "stored_rank_stability": stored_confidence,
                },
            ),
            _step(
                "swot-scope",
                "What this does and does not cover",
                "This SWOT describes the livelihood in this district. "
                "Personal fit comes from the recommendation step.",
                TrailFlag.NOTE,
                {"livelihood": display_livelihood, "district": district},
            ),
        ]
    }
