"""Raw-answer preview and scoring using the existing fuzzy and BN engines."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / "component1_audit"
sys.path.insert(0, str(PROJECT / "bn_engine"))
sys.path.insert(0, str(PROJECT / "fuzzy_engine"))
import bn_v0_1
import fuzzy_v0_1

REFERENCE_PATH = PROJECT / "outputs" / "stage4" / "reference_v0_1.json"
REFERENCE_DATA = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
REFERENCES = {key: fuzzy_v0_1.Reference.from_json(json.dumps({"sorted": values}))
              for key, values in REFERENCE_DATA["references"].items()}
ASSET_COUNT_FIELDS = ("d_01", "d_03", "d_05", "d_06", "d_08", "d_10", "d_17", "d_18", "d_19", "d_20", "d_21", "d_22", "d_23")
ASSET_BINARY_FIELDS = ("d_12", "d_13", "d_14", "d_15", "d_16")
ASSET_FIELDS = ASSET_COUNT_FIELDS + ASSET_BINARY_FIELDS
COUNT_TO_OWNED = {field: field for field in ASSET_COUNT_FIELDS}
WALL = {1: "durable", 2: "durable", 3: "durable", 4: "non_durable"}
FLOOR = {1: "durable", 2: "durable", 6: "durable", 3: "non_durable", 4: "non_durable", 5: "non_durable"}
ROOF = {1: "durable", 2: "durable", 3: "durable", 6: "non_durable"}
TOILET_IMPROVED = {1, 2, 3, 7, 9, 12}
TOILET_UNIMPROVED = {4, 6, 8, 11, 13}


def _number(value, name, *, integer=False, minimum=None, maximum=None):
    if value is None or value == "":
        return np.nan
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise HTTPException(422, f"{name}: enter a number or leave it blank for Unknown")
    if not np.isfinite(number) or (integer and not number.is_integer()) or (minimum is not None and number < minimum) or (maximum is not None and number > maximum):
        raise HTTPException(422, f"{name}: value is outside the allowed range")
    return int(number) if integer else number


def _code(value, name, allowed):
    number = _number(value, name, integer=True)
    if pd.isna(number):
        return None
    if number not in allowed:
        raise HTTPException(422, f"{name}: choose one of the listed codes or Unknown")
    return int(number)


def _derive(answers):
    ages = answers.get("roster_ages") or []
    if not isinstance(ages, list):
        raise HTTPException(422, "Roster ages must be a list")
    parsed_ages = []
    for index, value in enumerate(ages, 1):
        age = _number(value, f"Roster member {index} age", integer=True, minimum=0)
        parsed_ages.append(None if pd.isna(age) else age)
    known_ages = [age for age in parsed_ages if age is not None]
    n_under15 = sum(age < 15 for age in known_ages)
    n_working = sum(15 <= age <= 64 for age in known_ages)
    n_65plus = sum(age >= 65 for age in known_ages)
    dependency_ratio = (n_under15 + n_65plus) / n_working if n_working else None
    no_worker = int(n_working == 0) if known_ages else None

    bedrooms = _number(answers.get("bedrooms"), "Bedrooms", integer=True, minimum=0)
    persons_per_bedroom = len(parsed_ages) / bedrooms if not pd.isna(bedrooms) and bedrooms >= 1 and parsed_ages else None

    food = answers.get("food_answers") or []
    if not isinstance(food, list) or len(food) != 8:
        raise HTTPException(422, "Enter exactly eight food-insecurity answers; use Unknown for missing, Don't know, or Refused")
    fies_codes = [_code(value, f"Food item {index}", {1, 2, 3, 4}) for index, value in enumerate(food, 1)]
    fies_score = sum(code == 1 for code in fies_codes) if all(code in {1, 2} for code in fies_codes) else None

    material_codes = {
        "wall_code": _code(answers.get("wall_code"), "Wall material", set(range(1, 11)) | {999}),
        "floor_code": _code(answers.get("floor_code"), "Floor material", set(range(1, 8)) | {999}),
        "roof_code": _code(answers.get("roof_code"), "Roof material", set(range(1, 8)) | {999}),
    }
    tenure_code = _code(answers.get("tenure_code"), "Tenure", set(range(1, 9)) | {999})
    toilet_code = _code(answers.get("toilet_code"), "Toilet type", set(range(1, 15)) | {999})
    shared_code = _code(answers.get("toilet_shared"), "Toilet shared", {0, 1})

    assets = answers.get("assets") or {}
    if not isinstance(assets, dict):
        raise HTTPException(422, "Assets must be an object containing the 18 listed item codes")
    unexpected_assets = set(assets) - set(ASSET_FIELDS)
    if unexpected_assets:
        raise HTTPException(422, "Assets contain an item that is not in the 18-item codebook list")
    asset_values = {}
    owned_flags = []
    for field in ASSET_FIELDS:
        value = _number(assets.get(field), f"Asset {field}", integer=True, minimum=0)
        if not pd.isna(value):
            if field in ASSET_BINARY_FIELDS and value not in {0, 1}:
                raise HTTPException(422, f"Asset {field}: the cleaned-file code must be 0 (No) or 1 (Yes)")
            asset_values[field] = int(value)
            owned_flags.append(int(value > 0) if field in ASSET_COUNT_FIELDS else int(value == 1))
        else:
            asset_values[field] = None
            owned_flags.append(None)
    valid_assets = sum(value is not None for value in asset_values.values())
    owned_n = sum(flag for flag in owned_flags if flag is not None) if valid_assets else np.nan
    if valid_assets < 18:
        owned_n = np.nan  # Existing D-10a all-18-valid rule.

    income = _number(answers.get("monthly_income"), "Monthly household income", minimum=0)
    wall_class = WALL.get(material_codes["wall_code"]) if material_codes["wall_code"] is not None else None
    floor_class = FLOOR.get(material_codes["floor_code"]) if material_codes["floor_code"] is not None else None
    roof_class = ROOF.get(material_codes["roof_code"]) if material_codes["roof_code"] is not None else None
    if toilet_code in TOILET_IMPROVED:
        toilet_class = "basic" if shared_code == 0 else "limited" if shared_code == 1 else None
    elif toilet_code in TOILET_UNIMPROVED:
        toilet_class = "unimproved"
    elif toilet_code == 14:
        toilet_class = "open_defecation"
    else:
        # Codes 5, 10, and 999 remain Unknown while their classification is unresolved.
        toilet_class = None
    tenure_class = ("secure" if tenure_code in {1, 2, 3} else "intermediate" if tenure_code in {4, 5, 6}
                    else "insecure" if tenure_code in {7, 8} else None)
    raw = pd.DataFrame([{
        "fies_raw_score": fies_score,
        "persons_per_bedroom": persons_per_bedroom,
        "dependency_ratio": dependency_ratio,
        "no_working_age_member": no_worker,
        "income_value": income,
        "asset_types_owned_n": owned_n,
        "asset_items_valid_n": valid_assets,
        "tenure_class": tenure_class,
        "toilet_service_class": toilet_class,
        "wall_durability": wall_class,
        "floor_durability": floor_class,
        "roof_durability": roof_class,
    }])
    membership = fuzzy_v0_1.memberships(raw, REFERENCES)
    old_domains = fuzzy_v0_1.domain_degrees(membership)
    shelter_inputs = membership[["mu_wall", "mu_floor", "mu_roof"]]
    crowding_inputs = membership[["mu_crowding", "mu_tenure"]]
    leaves = {
        "shelter_quality": (shelter_inputs.mean(axis=1, skipna=True).iloc[0], int(shelter_inputs.notna().sum(axis=1).iloc[0]), 3),
        "sanitation": (membership.mu_toilet.iloc[0], int(membership.mu_toilet.notna().iloc[0]), 1),
        "crowding_tenure": (crowding_inputs.mean(axis=1, skipna=True).iloc[0], int(crowding_inputs.notna().sum(axis=1).iloc[0]), 2),
        "food": (membership.mu_food.iloc[0], int(membership.mu_food.notna().iloc[0]), 1),
        "demographic": (membership.mu_dependency.iloc[0], int(membership.mu_dependency.notna().iloc[0]), 1),
        "health": (np.nan, 0, 1),
        "economic": (old_domains.dom_economic.iloc[0], int(old_domains.dom_economic_n_used.iloc[0]), int(old_domains.dom_economic_n_total.iloc[0])),
        "financial_resilience": (np.nan, 0, 2),
    }
    preview = {
        "persons_per_bedroom": persons_per_bedroom,
        "dependency_ratio": dependency_ratio,
        "no_working_age_member": None if no_worker is None else bool(no_worker),
        "food_insecurity_score": fies_score,
        "valid_food_answers": sum(code in {1, 2} for code in fies_codes),
        "asset_items_valid": valid_assets,
        "asset_items_required": 18,
        "notes": ["Roster ages entered in this form are treated as the household roster; saved data roster inclusion rules are still under review.",
                  "Toilet codes 5, 10, and 999 remain Unknown because their classification is unresolved.",
                  "Health and financial-resilience inputs are not included in this raw form and remain Unknown in the v0.2 model."]
    }
    return {"membership": membership.iloc[0].to_dict(), "leaves": leaves, "preview": preview,
            "asset_values": asset_values, "material_codes": material_codes, "tenure_code": tenure_code,
            "toilet_code": toilet_code, "toilet_shared": shared_code}


def derive_assessment(answers):
    derived = _derive(answers)
    return {"preview": derived["preview"], "inputs": [
        {"id": key.removeprefix("mu_"), "value": None if pd.isna(value) else float(value)}
        for key, value in derived["membership"].items()
    ], "domains": {
        key: {"degree": None if pd.isna(value) else float(value), "n_used": n_used, "n_total": n_total}
        for key, (value, n_used, n_total) in derived["leaves"].items()
    }}


def score_assessment(answers, baseline_scores):
    derived = _derive(answers)
    frame = pd.DataFrame([{}])
    for leaf, (degree, n_used, n_total) in derived["leaves"].items():
        soft = fuzzy_v0_1.soft_levels(pd.Series([degree]))
        for state in ("low", "medium", "high"):
            frame[f"soft_{leaf}_{state}"] = soft[state].to_numpy()
        frame[f"dom_{leaf}_n_used"] = float(n_used)
        frame[f"dom_{leaf}_n_total"] = float(n_total)
    scored = bn_v0_1.score(frame, bn_v0_1.config_v02_interim()).iloc[0]
    nodes = {node: {state: float(scored[f"bn_{node}_{state}"]) for state in ("low", "medium", "high")}
             for node in ("living_conditions", "sensitivity", "adaptive_capacity", "vulnerability")}
    expected = float(scored.bn_expected_vulnerability)
    baseline = np.asarray(baseline_scores, dtype=float)
    percentile_rank = float(np.searchsorted(np.sort(baseline), expected, side="right") / len(baseline) * 100)
    total = sum(n_total for _, _, n_total in derived["leaves"].values())
    used = sum(n_used for _, n_used, _ in derived["leaves"].values())
    return {"expected_vulnerability": expected, "bn_p_high": float(scored.bn_p_high),
            "node_posteriors": nodes, "comparison_percentile": percentile_rank,
            "comparison_group": "Saved baseline household scores", "baseline_household_count": int(len(baseline)),
            "evidence_n_used": int(used), "evidence_n_total": int(total),
            "domain_coverage": {key: {"n_used": n_used, "n_total": n_total}
                                for key, (_, n_used, n_total) in derived["leaves"].items()},
            "preview": derived["preview"],
            "input_memberships": {key.removeprefix("mu_"): None if pd.isna(value) else float(value)
                                  for key, value in derived["membership"].items()}}
