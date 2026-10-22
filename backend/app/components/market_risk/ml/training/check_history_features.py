"""Check POST /api/risk/history-features against the training features (aggregates only).

Every keyed training row is rebuilt from that household's own earlier visits, using
only what the endpoint receives: the current visit_date and grant_date (full dates),
earlier visits as months, and the 4 answers per visit. The result of
services.compute_history_features must equal the training features exactly for all
14 history features; any mismatch makes the check fail (exit code 1).

Inputs (environment variables, files outside the repo):
    SUSTAIN_CLEANED   path to monitoring_visits_clean.csv
    SUSTAIN_COMBINED  path to combined.xlsx

From backend/:
    python -m app.components.market_risk.ml.training.check_history_features
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from app.components.market_risk import services
from app.components.market_risk.ml.training import features as fx
from app.components.market_risk.ml.training.xlsx_reader import read_xlsx

ANSWERS = {  # request field -> training signal (the request is positively worded)
    "business_running": "T_Business_Not_Running",
    "profit_last_month": "T_No_Profit_Last_Month",
    "progressing_well": "T_Not_Progressing_Well",
}


def _answers(row: pd.Series) -> dict[str, int | None]:
    out = {field: None if pd.isna(row[col]) else int(1 - row[col]) for field, col in ANSWERS.items()}
    out["market_stress"] = None if pd.isna(row["T_Market_Stress_Any"]) else int(row["T_Market_Stress_Any"])
    return out


def request_for(panel: pd.DataFrame, index: Any, grant_known: pd.Series) -> dict[str, Any] | None:
    """The request an officer would send for this row, or None if the row cannot be expressed."""
    row = panel.loc[index]
    if pd.isna(row["visit_date"]):
        return None
    earlier = panel[(panel["household_id"] == row["household_id"]) & (panel["Month_Ord"] < row["Month_Ord"])]
    grant = grant_known.loc[index]
    return {
        "current_visit": {
            "visit_date": row["visit_date"].date().isoformat(),
            **_answers(row),
            "grant_date": grant.date().isoformat() if pd.notna(grant) else None,
        },
        "previous_visits": [{"month": m, **_answers(r)} for m, (_, r) in zip(earlier["month"], earlier.iterrows())],
    }


def check(panel: pd.DataFrame, features: pd.DataFrame) -> dict[str, Any]:
    d = panel.sort_values(["household_id", "Month_Ord", "visit_id"])
    grant_ffill = d.groupby("household_id", sort=False)["grant_date"].transform(lambda s: s.ffill()).reindex(panel.index)
    # A grant date after the visit gives null in training; the endpoint rejects it, so it is not sent.
    grant_after_visit = grant_ffill.notna() & (grant_ffill > panel["visit_date"])
    grant_known = grant_ffill.where(~grant_after_visit)

    per_feature = {name: 0 for name in fx.HISTORY_FEATURES}
    rows_equal = skipped = 0
    for index in panel.index:
        request = request_for(panel, index, grant_known)
        if request is None:
            skipped += 1
            continue
        got = services.compute_history_features(request).features.model_dump()
        all_equal = True
        for name in fx.HISTORY_FEATURES:
            expected = features.at[index, name]
            same = (got[name] is None and pd.isna(expected)) or (
                got[name] is not None and not pd.isna(expected) and got[name] == float(expected)
            )
            per_feature[name] += int(same)
            all_equal &= same
        rows_equal += int(all_equal)

    checked = len(panel) - skipped
    return {
        "rows_checked": checked,
        "rows_skipped_no_visit_date": skipped,
        "rows_grant_after_visit_sent_as_null": int(grant_after_visit.sum()),
        "rows_all_14_equal": rows_equal,
        "row_match_rate": rows_equal / checked if checked else float("nan"),
        "per_feature_match_rate": {name: n / checked for name, n in per_feature.items()} if checked else {},
    }


def main(argv: list[str] | None = None) -> int:
    cleaned, combined = os.environ.get("SUSTAIN_CLEANED"), os.environ.get("SUSTAIN_COMBINED")
    if not cleaned or not combined:
        raise SystemExit("Set SUSTAIN_CLEANED and SUSTAIN_COMBINED (paths outside the repo)")
    sheets = read_xlsx(Path(combined).expanduser(), sheets=["Training_Table_HH_Month", "Category_Month_Table"])
    panel, _ = fx.build_panel(pd.read_csv(Path(cleaned).expanduser()), sheets["Training_Table_HH_Month"],
                              sheets["Category_Month_Table"])
    result = check(panel, fx.build_features(panel))
    print(json.dumps(result, indent=2))
    if result["rows_skipped_no_visit_date"] or result["rows_all_14_equal"] != result["rows_checked"]:
        print("FAIL: history features do not reproduce the training features on every row")
        return 1
    print("PASS: all 14 history features equal the training features on every row")
    return 0


if __name__ == "__main__":
    sys.exit(main())
