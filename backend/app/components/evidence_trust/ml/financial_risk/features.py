"""Feature construction kept in parity with Grant_Risk_Model.ipynb."""

from __future__ import annotations

import math
from typing import Any, Iterable

from .contracts import Visit

FEATURES = [
    "spent_pct", "spend_rate", "spend_change", "total_change", "remaining_up",
    "bills_streak", "slow_use", "not_per_plan", "business_running", "profit",
    "borrowed_money", "revenue_mid_lkr", "problem_count", "record_keeping_level",
    "saved_amount_lkr", "has_history", "revenue_missing", "form_incomplete",
]


def _to01(value: bool | int | float | str | None) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return math.nan
    if isinstance(value, str):
        if value.lower() == "true": return 1.0
        if value.lower() == "false": return 0.0
    return float(bool(value)) if isinstance(value, bool) else float(value)


def build_features(current: Visit, history: Iterable[Visit] = ()) -> dict[str, Any]:
    """Build one model row using only earlier visits of the same household."""
    earlier = [x for x in history if current.household_id and x.household_id == current.household_id and x.month_index < current.month_index]
    earlier.sort(key=lambda x: x.month_index)
    previous = earlier[-1] if earlier else None
    total = None if current.grant_spent_lkr is None or current.grant_remaining_lkr is None else current.grant_spent_lkr + current.grant_remaining_lkr
    prev_total = None if previous is None or previous.grant_spent_lkr is None or previous.grant_remaining_lkr is None else previous.grant_spent_lkr + previous.grant_remaining_lkr
    has_history = int(previous is not None)
    spend_change = 0.0 if previous is None or current.grant_spent_lkr is None or previous.grant_spent_lkr is None else current.grant_spent_lkr - previous.grant_spent_lkr
    total_change = 0.0 if prev_total is None or total is None else total - prev_total
    remaining_up = int(previous is not None and current.grant_remaining_lkr is not None and previous.grant_remaining_lkr is not None and current.grant_remaining_lkr > previous.grant_remaining_lkr)
    spent_pct = 0.0 if total in (None, 0) or current.grant_spent_lkr is None else current.grant_spent_lkr / total
    month = max(current.month_index, 1)
    unsettled = [x for x in earlier + [current] if x.grant_use_status == "Received, fully used, bills not settled"]
    bills_streak = 0
    for item in reversed(earlier + [current]):
        if item.grant_use_status != "Received, fully used, bills not settled": break
        bills_streak += 1
    values = {
        "spent_pct": spent_pct, "spend_rate": spent_pct / month, "spend_change": spend_change,
        "total_change": total_change, "remaining_up": remaining_up, "bills_streak": bills_streak,
        "slow_use": int(current.month_index >= 3 and spent_pct < 0.5),
        "not_per_plan": int(current.grant_used_per_plan is False),
        "business_running": _to01(current.business_running), "profit": _to01(current.profit),
        "borrowed_money": _to01(current.borrowed_money), "revenue_mid_lkr": current.revenue_mid_lkr,
        "problem_count": current.problem_count, "record_keeping_level": current.record_keeping_level,
        "saved_amount_lkr": current.saved_amount_lkr, "has_history": has_history,
        "revenue_missing": int(current.revenue_mid_lkr is None),
        "form_incomplete": int(any(x is None or (isinstance(x, float) and math.isnan(x)) for x in (current.profit, current.borrowed_money, current.problem_count, current.record_keeping_level))),
    }
    return values
