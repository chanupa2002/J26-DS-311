"""Research output - not an eligibility determination.

Strict adapter from the Stage 3 household table to fuzzy_v0_1's input contract.
It performs only explicit field mapping, numeric parsing, and unknown handling.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

LABEL = "Research output - not an eligibility determination"
CONTRACT = ["hhcode", "fies_raw_score", "persons_per_bedroom", "dependency_ratio",
            "no_working_age_member", "income_value", "asset_types_owned_n",
            "asset_items_valid_n", "tenure_class", "toilet_service_class",
            "wall_durability", "floor_durability", "roof_durability"]

def _numeric_or_nan(series):
    return pd.to_numeric(series, errors="coerce")

def _category_or_nan(series, allowed):
    result = series.astype("string").str.strip()
    result = result.where(result.isin(allowed), pd.NA)
    return result.astype(object).where(result.notna(), np.nan)

def adapt(stage3: pd.DataFrame):
    """Return (engine_input, coverage) without deriving new indicators.

    Proxy fields are rejected. A missing Stage 3 contract field is represented
    as unknown and reported rather than inferred from another field.
    """
    proxies = {"label_high_vuln", "pc_cons"} & set(stage3.columns)
    if proxies:
        raise ValueError(f"Forbidden proxy column(s) in adapter input: {sorted(proxies)}")
    out = pd.DataFrame(index=stage3.index)
    out["hhcode"] = stage3["hhcode"] if "hhcode" in stage3 else pd.NA
    numeric = {
        "fies_raw_score": "fies_raw_score",
        "persons_per_bedroom": "persons_per_bedroom",
        "dependency_ratio": "dependency_ratio",
        "no_working_age_member": "no_working_age_member",
        "asset_types_owned_n": "asset_types_owned_n",
        "asset_items_valid_n": "asset_items_valid_n",
    }
    for target, source in numeric.items():
        out[target] = _numeric_or_nan(stage3[source]) if source in stage3 else np.nan
    if "h1_17_raw_household_value" in stage3:
        income = _numeric_or_nan(stage3["h1_17_raw_household_value"])
        if "h1_17_consistency_status" in stage3:
            income = income.where(stage3["h1_17_consistency_status"].eq("consistent_repeated_value"))
        else:
            income[:] = np.nan
        out["income_value"] = income
    else:
        out["income_value"] = np.nan
    out["tenure_class"] = _category_or_nan(stage3["tenure_class"], {"secure", "intermediate", "insecure"}) if "tenure_class" in stage3 else np.nan
    out["toilet_service_class"] = _category_or_nan(stage3["toilet_service_class"], {"basic", "limited", "unimproved", "open_defecation"}) if "toilet_service_class" in stage3 else np.nan
    for target, source in [("wall_durability", "c1_04_durability_class"),
                           ("floor_durability", "c1_05_durability_class"),
                           ("roof_durability", "c1_06_durability_class")]:
        out[target] = _category_or_nan(stage3[source], {"durable", "non_durable"}) if source in stage3 else np.nan
    out = out[CONTRACT]
    coverage = []
    for column in CONTRACT:
        if column == "hhcode":
            continue
        s = out[column]
        coverage.append({"label": LABEL, "engine_input": column, "stage3_source": _source_for(column),
                         "rows": len(out), "known_n": int(s.notna().sum()),
                         "unknown_n": int(s.isna().sum()), "known_rate": float(s.notna().mean()) if len(s) else np.nan})
    # Diagnostic coverage only; these five Stage 3 item fields are not engine inputs.
    for column in [f"d_{i:02d}_owned" for i in range(12, 17)]:
        s = pd.to_numeric(stage3[column], errors="coerce") if column in stage3 else pd.Series(np.nan, index=stage3.index)
        coverage.append({"label": LABEL, "engine_input": column, "stage3_source": column,
                         "rows": len(stage3), "known_n": int(s.notna().sum()),
                         "unknown_n": int(s.isna().sum()), "known_rate": float(s.notna().mean()) if len(s) else np.nan,
                         "note": "coverage diagnostic only; engine consumes Stage 3 aggregate asset fields unchanged"})
    return out, pd.DataFrame(coverage)

def _source_for(column):
    return {
        "income_value": "h1_17_raw_household_value where h1_17_consistency_status=consistent_repeated_value",
        "wall_durability": "c1_04_durability_class exact durable/non_durable only",
        "floor_durability": "c1_05_durability_class exact durable/non_durable only",
        "roof_durability": "c1_06_durability_class exact durable/non_durable only",
    }.get(column, column)
