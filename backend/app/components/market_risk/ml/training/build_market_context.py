"""Build ml/market_context.json: the 13 market and macro features per (category, month).

Market features depend only on (category, month) and macro features only on month,
so an officer cannot know them; GET /api/risk/market-context serves them from this
lookup. It uses the SAME join and formulas as training (features.join_market_macro
and features.market_macro_features): Category_Month_Table rows with Row_Basis "ALL"
by (month, category key), macro columns by month.

The file holds ONLY aggregated public indicators (category price-pressure and
volatility lines, CCPI, CCPI food index, auto diesel price) per category key and
month. No household rows, IDs or survey answers.

Inputs (environment variables):
    SUSTAIN_COMBINED  path to combined.xlsx (required)
    SUSTAIN_CLEANED   path to monitoring_visits_clean.csv (only for --verify)

From backend/:
    python -m app.components.market_risk.ml.training.build_market_context [--verify] [--out PATH]
"""

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from app.components.market_risk.ml.training import features as fx
from app.components.market_risk.ml.training.xlsx_reader import read_xlsx

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "market_context.json"
OTHER_KEY = "OTHER"  # the trained level "Other" also covers FISHERIES & AQUACULTURE and MISCELLANEOUS
SOURCE_NOTE = (
    "Category market indicators (primary price-pressure and volatility lines and their tiers, "
    "Category_Month_Table, Row_Basis ALL) and national macro indicators (CCPI YoY inflation, "
    "CCPI food index, auto diesel price) from the project's combined training workbook. "
    "Aggregated public indicators only; same join and formulas as model training."
)


def _json_value(value: Any) -> float | None:
    """NaN -> None (JSON null); numbers as float, which round-trips exactly through JSON."""
    return None if pd.isna(value) else float(value)


def level_keys(key_to_level: dict[str, str]) -> dict[str, str]:
    """Trained level -> the category key used when only the level is given."""
    result: dict[str, str] = {}
    for key, level in key_to_level.items():
        if level == "Other":
            result[level] = OTHER_KEY
        else:
            result.setdefault(level, key)
    return result


def build_lookup(category_month: pd.DataFrame, created: str | None = None) -> dict[str, Any]:
    """Every category key x every month in the table, computed exactly as in training."""
    months = sorted(category_month["Month"].astype(str).unique())
    keys = sorted(fx.KEY_TO_LEVEL)
    grid = pd.DataFrame([(m, k) for k in keys for m in months], columns=["Month", "Category_Key"])
    joined = fx.join_market_macro(grid["Month"], grid["Category_Key"], category_month)
    F = fx.market_macro_features(joined)

    market: dict[str, dict[str, dict]] = {key: {} for key in keys}
    macro: dict[str, dict] = {}
    for i, row in grid.iterrows():
        market[row.Category_Key][row.Month] = {f: _json_value(F.at[i, f]) for f in fx.MARKET_FEATURES}
        macro.setdefault(row.Month, {f: _json_value(F.at[i, f]) for f in fx.MACRO_FEATURES})
    for values in market.values():
        for entry in values.values():
            entry["F_Mkt_Evidence_Missing"] = int(entry["F_Mkt_Evidence_Missing"])

    return {
        "description": "Market (per category key and month) and macro (per month) model features for GET /api/risk/market-context. Aggregated public indicators only; no household data.",
        "created": created or dt.datetime.now().isoformat(timespec="seconds"),
        "source_note": SOURCE_NOTE,
        "built_by": "ml/training/build_market_context.py",
        "months": months,
        "category_keys": dict(sorted(fx.KEY_TO_LEVEL.items())),
        "level_keys": dict(sorted(level_keys(fx.KEY_TO_LEVEL).items())),
        "market_features": fx.MARKET_FEATURES,
        "macro_features": fx.MACRO_FEATURES,
        "market": market,
        "macro": macro,
    }


def lookup_values(lookup: dict[str, Any], category_key: str, month: str) -> dict[str, Any] | None:
    """The 13 values for (category key, month), or None if the month is not in the lookup."""
    if month not in lookup["macro"]:
        return None
    return {**lookup["market"][category_key][month], **lookup["macro"][month]}


def verify(panel: pd.DataFrame, features: pd.DataFrame, lookup: dict[str, Any]) -> dict[str, Any]:
    """Compare the lookup with the training features on every keyed panel row (exact equality)."""
    rows_equal = values_equal = values_checked = 0
    for index, row in panel.iterrows():
        expected = lookup_values(lookup, row["category_key"], row["month"])
        all_equal = expected is not None
        for f in fx.CONTEXT_FEATURES:
            a = features.at[index, f]
            b = None if expected is None else expected[f]
            same = (b is None and pd.isna(a)) or (b is not None and not pd.isna(a) and float(a) == float(b))
            values_checked += 1
            values_equal += int(same)
            all_equal &= same
        rows_equal += int(all_equal)
    return {
        "rows_checked": int(len(panel)),
        "rows_all_13_equal": rows_equal,
        "row_match_rate": rows_equal / len(panel) if len(panel) else float("nan"),
        "values_checked": values_checked,
        "values_equal": values_equal,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output JSON (default ml/market_context.json)")
    parser.add_argument("--verify", action="store_true",
                        help="also compare with the training features on every keyed row (needs SUSTAIN_CLEANED)")
    args = parser.parse_args(argv)

    combined = os.environ.get("SUSTAIN_COMBINED")
    if not combined:
        raise SystemExit("Set SUSTAIN_COMBINED to the path of combined.xlsx")
    sheets = read_xlsx(Path(combined).expanduser(), sheets=["Category_Month_Table", "Training_Table_HH_Month"])
    lookup = build_lookup(sheets["Category_Month_Table"])

    if args.verify:
        cleaned = os.environ.get("SUSTAIN_CLEANED")
        if not cleaned:
            raise SystemExit("Set SUSTAIN_CLEANED for --verify")
        panel, _ = fx.build_panel(pd.read_csv(Path(cleaned).expanduser()), sheets["Training_Table_HH_Month"],
                                  sheets["Category_Month_Table"])
        result = verify(panel, fx.build_features(panel), lookup)
        print(json.dumps(result, indent=2))
        if result["rows_all_13_equal"] != result["rows_checked"]:
            raise SystemExit("STOP: the lookup does not reproduce the training features; file not written")

    args.out.write_text(json.dumps(lookup, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out.name}: {len(lookup['market'])} category keys x {len(lookup['months'])} months")
    return 0


if __name__ == "__main__":
    sys.exit(main())
