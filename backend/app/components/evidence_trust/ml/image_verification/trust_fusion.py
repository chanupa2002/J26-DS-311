"""Convert image-verification results into Trust Fusion inputs."""

from __future__ import annotations

from typing import Any

from .contracts import CheckResult, ImageReport


def _value(checks: dict[str, CheckResult], code: str) -> Any:
    check = checks.get(code)
    return check.value if check and check.value is not None else "not available"


def to_trust_fusion_inputs(report: ImageReport) -> dict[str, Any]:
    """Return confidence inputs while preserving unknowns as unavailable."""
    checks = {check.check_code: check for block in report.blocks for check in block.checks}
    quality_score = next((check.raw_measure for check in checks.values() if check.check_code == "QUALITY_USABLE" and isinstance(check.raw_measure, (int, float))), "not available")
    duplicate_cross = checks.get("DUPLICATE_CROSS")
    duplicate_self = checks.get("DUPLICATE_SELF")
    confirmed_duplicate = bool(duplicate_cross and duplicate_cross.value == 0) or bool(duplicate_self and duplicate_self.value == 0)
    return {
        "quality": {"usable": _value(checks, "QUALITY_USABLE"), "quality_score": quality_score},
        "duplicate": {"self": _value(checks, "DUPLICATE_SELF"), "cross": _value(checks, "DUPLICATE_CROSS"), "confirmed_duplicate": confirmed_duplicate, "severity": "critical" if confirmed_duplicate else "not available" if duplicate_cross is None and duplicate_self is None else "review"},
        "category_match": {"value": _value(checks, "CATEGORY_MATCH"), "predicted_category": (checks.get("CATEGORY_MATCH").evidence.get("predicted_category") if checks.get("CATEGORY_MATCH") else "not available"), "confidence": (checks.get("CATEGORY_MATCH").evidence.get("calibrated_confidence") if checks.get("CATEGORY_MATCH") else "not available")},
        "confidence_reduction_reasons": [check.check_code for check in report.unknown_checks],
    }
