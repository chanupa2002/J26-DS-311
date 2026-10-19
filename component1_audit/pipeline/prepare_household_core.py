"""Build a minimal, auditable household core from the delivered BRIGHT files.

This first version implements only the household key spine and a direct count of
unique roster member IDs. It does not calculate vulnerability indicators.
Inputs are read-only; generated data remain in the ignored outputs directory.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CLEAN_DIR = Path(os.environ.get("BRIGHT_CLEAN_DIR", r"C:\data\processed\clean"))
if not CLEAN_DIR.is_dir():
    CLEAN_DIR = ROOT / "Data" / "processed" / "clean"
OUT_DIR = Path(os.environ.get("BRIGHT_OUTPUT_DIR", str(ROOT / "component1_audit" / "outputs" / "pipeline_v0")))
MASTER_FILE = "mod_a_household_identification.csv"
ROSTER_FILE = "mod_b0_roster_long.csv"
L1_FILE = "mod_l1_food_security_w.csv"
L2_FILE = "mod_l2_food_security_m.csv"
CONTEXT_FILE = "hh_context.csv"
HOUSING_FILE = "mod_c_housing.csv"
ASSET_FILE = "mod_d_assets.csv"
H1_FILE = "mod_h1_primary_employment_long.csv"
ASSET_ITEMS = ["d_01", "d_03", "d_05", "d_06", "d_08", "d_10", "d_12", "d_13", "d_14",
               "d_15", "d_16", "d_17", "d_18", "d_19", "d_20", "d_21", "d_22", "d_23"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_required(path: Path, required: set[str], dtype: dict | str | None = None) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required BRIGHT input is missing: {path}")
    frame = pd.read_csv(path, dtype=dtype or {"hhcode": "string", "pid": "string"})
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {sorted(missing)}")
    return frame


def build_household_core(master: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    """Return one row per master hhcode; do not turn absent roster into zero."""
    if master["hhcode"].isna().any() or master["hhcode"].duplicated().any():
        raise ValueError("Household master hhcode must be nonmissing and unique")
    if roster[["hhcode", "pid"]].isna().any().any():
        raise ValueError("Roster hhcode and pid must be nonmissing for member counting")
    if roster.duplicated(["hhcode", "pid"]).any():
        raise ValueError("Roster contains duplicate hhcode + pid keys")

    outside_master = ~roster["hhcode"].isin(master["hhcode"])
    if outside_master.any():
        raise ValueError("Roster contains household keys absent from the declared master")

    counts = (roster.groupby("hhcode", sort=False)["pid"]
              .nunique(dropna=True).rename("roster_member_count").reset_index())
    result = master[["hhcode"]].merge(counts, how="left", on="hhcode", validate="one_to_one", sort=False)
    if len(result) != len(master) or result["hhcode"].tolist() != master["hhcode"].tolist():
        raise AssertionError("Household spine changed during roster aggregation")
    # Unmatched roster remains NA: absence is not interpreted as a zero-member household.
    return result


def build_fies_item_extract(master: pd.DataFrame, l1: pd.DataFrame, l2: pd.DataFrame) -> pd.DataFrame:
    """Keep L1/L2 response codes separate; do not calculate a household score."""
    if master["hhcode"].isna().any() or master["hhcode"].duplicated().any():
        raise ValueError("Household master hhcode must be nonmissing and unique")
    pieces = []
    for frame, prefix in ((l1, "l1"), (l2, "l2")):
        expected = {"hhcode", f"{prefix}_answered", *{f"{prefix}_{i:02d}" for i in range(1, 9)}}
        missing = expected.difference(frame.columns)
        if missing:
            raise ValueError(f"{prefix.upper()} FIES file is missing required columns: {sorted(missing)}")
        if frame.hhcode.isna().any() or frame.hhcode.duplicated().any():
            raise ValueError(f"{prefix.upper()} FIES household key must be nonmissing and unique")
        cols = ["hhcode", f"{prefix}_answered", *[f"{prefix}_{i:02d}" for i in range(1, 9)]]
        pieces.append(frame[cols].copy())
    result = master[["hhcode"]].merge(pieces[0], on="hhcode", how="left", validate="one_to_one", sort=False)
    result = result.merge(pieces[1], on="hhcode", how="left", validate="one_to_one", sort=False)
    if len(result) != len(master) or result.hhcode.tolist() != master.hhcode.tolist():
        raise AssertionError("FIES item extraction changed the household spine")
    return result


def build_proxy_reference(master: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    """Isolated copy of the unvalidated prepared proxy for descriptive sensitivity only."""
    if context.hhcode.isna().any() or context.hhcode.duplicated().any():
        raise ValueError("Prepared context hhcode must be nonmissing and unique")
    needed = {"hhcode", "pc_cons", "label_high_vuln"}
    missing = needed.difference(context.columns)
    if missing:
        raise ValueError(f"Prepared context is missing proxy reference columns: {sorted(missing)}")
    selected = context[["hhcode", "pc_cons", "label_high_vuln"]].rename(columns={
        "pc_cons": "pc_cons_prepared_unvalidated",
        "label_high_vuln": "label_high_vuln_prepared_unvalidated",
    })
    result = master[["hhcode"]].merge(selected, on="hhcode", how="left", validate="one_to_one", sort=False)
    if len(result) != len(master) or result.hhcode.tolist() != master.hhcode.tolist():
        raise AssertionError("Proxy reference extract changed the household spine")
    return result


def build_d1_source_candidates(master: pd.DataFrame, housing: pd.DataFrame,
                               assets: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    """Keep selected D1 item responses raw; collapse H1_17 only when identical."""
    if master.hhcode.isna().any() or master.hhcode.duplicated().any():
        raise ValueError("Household master hhcode must be nonmissing and unique")
    for frame, label, required in (
        (housing, "Housing", {"hhcode", "c1_04", "c1_05", "c1_06", "c1_07", "c1_08"}),
        (assets, "Assets", {"hhcode", *ASSET_ITEMS}),
    ):
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{label} file is missing required columns: {sorted(missing)}")
        if frame.hhcode.isna().any() or frame.hhcode.duplicated().any():
            raise ValueError(f"{label} household key must be nonmissing and unique")
        if (~frame.hhcode.isin(master.hhcode)).any():
            raise ValueError(f"{label} module contains household keys absent from master")

    if not {"hhcode", "hhmember", "h1_17"}.issubset(h1.columns):
        raise ValueError("H1 file requires hhcode, hhmember, and h1_17")
    if h1[["hhcode", "hhmember"]].isna().any().any() or h1.duplicated(["hhcode", "hhmember"]).any():
        raise ValueError("H1 employment person key hhcode + hhmember must be complete and unique")
    if (~h1.hhcode.isin(master.hhcode)).any():
        raise ValueError("H1 module contains household keys absent from master")

    def summarize(values: pd.Series) -> pd.Series:
        observed = [str(x).strip() for x in values if pd.notna(x) and str(x).strip() != ""]
        distinct = list(dict.fromkeys(observed))
        return pd.Series({
            "h1_17_nonmissing_record_count": len(observed),
            "h1_17_distinct_nonmissing_value_count": len(distinct),
            "h1_17_raw_household_value": distinct[0] if len(distinct) == 1 else pd.NA,
            "h1_17_consistency_status": (
                "no_nonmissing_record_value" if len(distinct) == 0 else
                "consistent_repeated_value" if len(distinct) == 1 else "conflicting_values"
            ),
        })

    h1_hh = h1.groupby("hhcode", sort=False)["h1_17"].apply(summarize).unstack().reset_index()
    h1_hh["h1_17_nonmissing_record_count"] = h1_hh["h1_17_nonmissing_record_count"].astype("int64")
    h1_hh["h1_17_distinct_nonmissing_value_count"] = h1_hh["h1_17_distinct_nonmissing_value_count"].astype("int64")

    result = master[["hhcode"]].merge(housing[["hhcode", "c1_04", "c1_05", "c1_06", "c1_07", "c1_08"]],
                                       on="hhcode", how="left", validate="one_to_one", sort=False)
    result = result.merge(assets[["hhcode", *ASSET_ITEMS]], on="hhcode", how="left", validate="one_to_one", sort=False)
    result = result.merge(h1_hh, on="hhcode", how="left", validate="one_to_one", sort=False)
    no_h1_record = result["h1_17_consistency_status"].isna()
    result.loc[no_h1_record, "h1_17_consistency_status"] = "no_h1_record"
    result.loc[no_h1_record, ["h1_17_nonmissing_record_count", "h1_17_distinct_nonmissing_value_count"]] = 0
    result["h1_17_nonmissing_record_count"] = result["h1_17_nonmissing_record_count"].astype("int64")
    result["h1_17_distinct_nonmissing_value_count"] = result["h1_17_distinct_nonmissing_value_count"].astype("int64")
    if len(result) != len(master) or result.hhcode.tolist() != master.hhcode.tolist():
        raise AssertionError("D1 source candidate extraction changed the household spine")
    return result


def build_d3_person_items(roster: pd.DataFrame, b3: pd.DataFrame) -> pd.DataFrame:
    """Preserve person-level ages and B3 answers without household rollup."""
    roster_cols = {"hhcode", "pid", "b0_04_years", "b0_04_months"}
    b3_cols = {"hhcode", "pid", "b3_01", "b3_02", "b3_03"}
    if missing := roster_cols.difference(roster.columns):
        raise ValueError(f"B0 roster is missing required columns: {sorted(missing)}")
    if missing := b3_cols.difference(b3.columns):
        raise ValueError(f"B3 module is missing required columns: {sorted(missing)}")
    person_key = ["hhcode", "pid"]
    for frame, label in ((roster, "B0 roster"), (b3, "B3 module")):
        if frame[person_key].isna().any().any() or frame.duplicated(person_key).any():
            raise ValueError(f"{label} person key hhcode + pid must be complete and unique")
    roster_keys = pd.MultiIndex.from_frame(roster[person_key])
    b3_keys = pd.MultiIndex.from_frame(b3[person_key])
    if not b3_keys.isin(roster_keys).all():
        raise ValueError("B3 module contains person keys absent from the B0 roster")

    left = roster[[*person_key, "b0_04_years", "b0_04_months"]].copy()
    right = b3[[*person_key, "b3_01", "b3_02", "b3_03"]].copy()
    result = left.merge(right, on=person_key, how="left", validate="one_to_one", sort=False, indicator=True)
    result["b3_module_record_present"] = result.pop("_merge").eq("both")
    if len(result) != len(roster) or result[person_key].to_records(index=False).tolist() != roster[person_key].to_records(index=False).tolist():
        raise AssertionError("D3 person extract changed roster keys or row count")
    return result


def main() -> None:
    master_path = CLEAN_DIR / MASTER_FILE
    roster_path = CLEAN_DIR / ROSTER_FILE
    master = read_required(master_path, {"hhcode"})
    roster = read_required(roster_path, {"hhcode", "pid", "b0_04_years", "b0_04_months"}, dtype="string")
    output = build_household_core(master, roster)
    l1_path, l2_path = CLEAN_DIR / L1_FILE, CLEAN_DIR / L2_FILE
    context_path = Path(os.environ.get("BRIGHT_PROCESSED_DIR", r"C:\data\processed")) / CONTEXT_FILE
    if not context_path.is_file():
        context_path = ROOT / "Data" / "processed" / CONTEXT_FILE
    l1 = read_required(l1_path, {"hhcode", "l1_answered", *{f"l1_{i:02d}" for i in range(1, 9)}})
    l2 = read_required(l2_path, {"hhcode", "l2_answered", *{f"l2_{i:02d}" for i in range(1, 9)}})
    context = read_required(context_path, {"hhcode", "pc_cons", "label_high_vuln"})
    fies = build_fies_item_extract(master, l1, l2)
    proxy = build_proxy_reference(master, context)
    housing_path, asset_path, h1_path = CLEAN_DIR / HOUSING_FILE, CLEAN_DIR / ASSET_FILE, CLEAN_DIR / H1_FILE
    housing = read_required(housing_path, {"hhcode", "c1_04", "c1_05", "c1_06", "c1_07", "c1_08"}, dtype="string")
    assets = read_required(asset_path, {"hhcode", *ASSET_ITEMS}, dtype="string")
    h1 = read_required(h1_path, {"hhcode", "hhmember", "h1_17"}, dtype={"hhcode": "string", "hhmember": "string", "h1_17": "string"})
    d1_pending = build_d1_source_candidates(master, housing, assets, h1)
    b3_path = CLEAN_DIR / "mod_b3_roster_long.csv"
    b3 = read_required(b3_path, {"hhcode", "pid", "b3_01", "b3_02", "b3_03"}, dtype="string")
    d3_person_pending = build_d3_person_items(roster, b3)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUT_DIR / "household_core.csv"
    output.to_csv(output_path, index=False, na_rep="")
    fies_path = OUT_DIR / "fies_item_responses_pending.csv"
    fies.to_csv(fies_path, index=False, na_rep="")
    proxy_path = OUT_DIR / "proxy_sensitivity_reference.csv"
    proxy.to_csv(proxy_path, index=False, na_rep="")
    d1_path = OUT_DIR / "d1_observed_candidates_pending.csv"
    d1_pending.to_csv(d1_path, index=False, na_rep="")
    d3_path = OUT_DIR / "d3_person_items_pending.csv"
    d3_person_pending.to_csv(d3_path, index=False, na_rep="")
    manifest = {
        "pipeline_version": "0.1.0",
        "scope": "household key spine and direct unique-roster-member count only",
        "population_rows": int(len(output)),
        "household_keys_unique_nonmissing": bool(output.hhcode.notna().all() and output.hhcode.is_unique),
        "roster_member_count_missing": int(output.roster_member_count.isna().sum()),
        "inputs": {
            MASTER_FILE: {"sha256": sha256(master_path), "rows": int(len(master))},
            ROSTER_FILE: {"sha256": sha256(roster_path), "rows": int(len(roster))},
        },
        "output": output_path.name,
        "companion_outputs": {
            fies_path.name: "L1/L2 raw item codes kept in separate columns; no combined score",
            proxy_path.name: "Prepared proxy copy for descriptive sensitivity only; excluded from core and model features",
            d1_path.name: "Raw D1 housing/assets; H1_17 retained as one raw household value only when repeated records agree; no classification or recoding",
            d3_path.name: "Person-level B0 age and B3 item responses joined one-to-one by household/person key; no household aggregation or recoding",
        },
        "additional_inputs": {
            L1_FILE: {"sha256": sha256(l1_path), "rows": int(len(l1))},
            L2_FILE: {"sha256": sha256(l2_path), "rows": int(len(l2))},
            CONTEXT_FILE: {"sha256": sha256(context_path), "rows": int(len(context))},
            HOUSING_FILE: {"sha256": sha256(housing_path), "rows": int(len(housing))},
            ASSET_FILE: {"sha256": sha256(asset_path), "rows": int(len(assets))},
            H1_FILE: {"sha256": sha256(h1_path), "rows": int(len(h1))},
            "mod_b0_roster_long.csv": {"sha256": sha256(roster_path), "rows": int(len(roster))},
            "mod_b3_roster_long.csv": {"sha256": sha256(b3_path), "rows": int(len(b3))},
        },
        "unresolved_methodology": [
            "This count is not asserted to equal the questionnaire's defined household size.",
            "No new D1-D7 indicators, imputed values, proxy labels, weights, or model scores are calculated; the existing proxy is copied only to a separate descriptive reference file.",
            "The 6,847 versus 6,850 survey denominator remains unresolved.",
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "inputs"}, indent=2))


if __name__ == "__main__":
    main()
