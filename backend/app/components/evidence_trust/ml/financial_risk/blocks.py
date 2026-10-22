"""Financial-risk processing blocks."""

from __future__ import annotations

from typing import Any

from .contracts import CheckResult, Visit
from .features import build_features
from .scoring import calculate_scores


def reliability_block(visit: Visit, config: dict[str, Any]) -> tuple[dict[str, Any], list[CheckResult]]:
    applicable = [visit.profit, visit.borrowed_money, visit.problem_count, visit.record_keeping_level, visit.revenue_mid_lkr]
    answered = sum(x is not None for x in applicable)
    completeness = answered / len(applicable) if applicable else 1.0
    thresholds = config.get("reliability", {"high": 0.9, "medium": 0.6})
    level = "High" if completeness >= thresholds["high"] else "Medium" if completeness >= thresholds["medium"] else "Low"
    return {"completeness": completeness, "applicable": len(applicable), "answered": answered, "level": level}, []


def ledger_block(visit: Visit, history: list[Visit], config: dict[str, Any]) -> list[CheckResult]:
    checks: list[CheckResult] = []
    if visit.grant_spent_lkr is None or visit.grant_remaining_lkr is None:
        checks.append(CheckResult("BALANCE_MISMATCH", None, "Grant amounts are unavailable.", {"grant_amount": config["grant_amount"]}))
        checks.append(CheckResult("STATUS_BALANCE_CONFLICT", None, "Grant amounts are unavailable."))
    else:
        expected = float(config["grant_amount"])
        actual = visit.grant_spent_lkr + visit.grant_remaining_lkr
        mismatch = abs(actual - expected) > expected * float(config["tolerance"])
        checks.append(CheckResult("BALANCE_MISMATCH", 0 if mismatch else 1, "Spent plus remaining differs from the configured grant amount." if mismatch else "Grant balance is within tolerance.", {"actual_total": actual, "grant_amount": expected, "tolerance": config["tolerance"]}, "review" if mismatch else "info"))
        status = visit.grant_use_status or ""
        status_lower = status.lower()
        conflict = (("not fully used" not in status_lower and "fully used" in status_lower and visit.grant_remaining_lkr > 0) or ("not fully used" in status_lower and visit.grant_remaining_lkr == 0))
        checks.append(CheckResult("STATUS_BALANCE_CONFLICT", 0 if conflict else 1, "Lifecycle status conflicts with the remaining balance." if conflict else "Lifecycle status is consistent with the remaining balance.", {"status": status, "remaining": visit.grant_remaining_lkr}, "review" if conflict else "info"))
    if history and config.get("switches", {}).get("cross_month", True):
        previous = max((x for x in history if visit.household_id and x.household_id == visit.household_id and x.month_index < visit.month_index), key=lambda x: x.month_index, default=None)
        if previous:
            def comparison(code: str, fired: bool, reason: str, measures: dict[str, Any]) -> None:
                checks.append(CheckResult(code, 0 if fired else 1, reason if fired else "No cross-month issue detected.", measures, "review" if fired else "info"))
            if visit.grant_spent_lkr is not None and previous.grant_spent_lkr is not None: comparison("SPENT_DECREASED", visit.grant_spent_lkr < previous.grant_spent_lkr, "Reported spending decreased compared with the previous visit.", {"previous": previous.grant_spent_lkr, "current": visit.grant_spent_lkr})
            if visit.grant_remaining_lkr is not None and previous.grant_remaining_lkr is not None: comparison("BALANCE_INCREASED", visit.grant_remaining_lkr > previous.grant_remaining_lkr, "Reported remaining balance increased compared with the previous visit.", {"previous": previous.grant_remaining_lkr, "current": visit.grant_remaining_lkr})
            regression = bool(previous.grant_use_status and visit.grant_use_status and "fully used" in previous.grant_use_status.lower() and "fully used" not in visit.grant_use_status.lower())
            comparison("STATUS_REGRESSION", regression, "Grant lifecycle status moved backwards compared with the previous visit.", {"previous": previous.grant_use_status, "current": visit.grant_use_status})
            stalled = visit.grant_spent_lkr == previous.grant_spent_lkr if visit.grant_spent_lkr is not None and previous.grant_spent_lkr is not None else False
            checks.append(CheckResult("GRANT_STALLED", 0 if stalled else 1, "Grant spending did not change; support follow-up may be useful." if stalled else "Grant spending changed.", {"previous": previous.grant_spent_lkr, "current": visit.grant_spent_lkr}, "advisory" if stalled else "info"))
    consistency_inputs = [x for x in checks if x.code in {"BALANCE_MISMATCH", "STATUS_BALANCE_CONFLICT"}]
    if not consistency_inputs or any(x.value is None for x in consistency_inputs):
        consistency = None
    else:
        consistency = 0 if any(x.value == 0 for x in consistency_inputs) else 1
    checks.append(CheckResult("FINANCIAL_CONSISTENCY", consistency, "Ledger consistency failed and needs review." if consistency == 0 else "Ledger consistency checks passed." if consistency == 1 else "Ledger consistency is unknown.", severity="review" if consistency == 0 else "info"))
    return checks


def context_block(visit: Visit) -> list[CheckResult]:
    return [CheckResult("DISASTER_IMPACT_REPORTED", 0 if visit.disaster_impact_reported else 1, "A disaster impact was reported." if visit.disaster_impact_reported else "No disaster impact was reported.", severity="info"), CheckResult("LIVELIHOOD_DIFFICULTY_REPORTED", 0 if visit.livelihood_difficulty_reported else 1, "A livelihood difficulty was reported." if visit.livelihood_difficulty_reported else "No livelihood difficulty was reported.", severity="info"), CheckResult("BUSINESS_NOT_RUNNING", 0 if visit.business_running is False else 1 if visit.business_running is True else None, "The business was reported as not running." if visit.business_running is False else "Business-running status is unknown." if visit.business_running is None else "The business was reported as running.", severity="info")]


def advisory_block(features: dict[str, Any], artifact: dict[str, Any] | None, config: dict[str, Any], score_samples: Any = None) -> tuple[list[CheckResult], dict[str, Any]]:
    scored = calculate_scores(features, artifact, config, score_samples)
    level = scored["level"]
    value = None if level is None else 0 if level in config.get("flag_levels", ["High"]) else 1
    reason = "; ".join(x["text"] for x in scored["hits"]) or ("No configured advisory rule fired." if level else "Model artifact unavailable.")
    check = CheckResult("ANOMALY_RISK", value, reason, {k: scored[k] for k in ("rule_score", "model_score", "risk", "level", "thresholds") if k in scored} | {"thresholds": config["thresholds"]}, "review")
    return [check], scored
