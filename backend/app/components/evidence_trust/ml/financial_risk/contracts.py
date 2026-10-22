"""Typed contracts for the financial-risk module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Literal

CheckValue = Literal[0, 1] | None


@dataclass(slots=True)
class Visit:
    """A monitoring visit. Household identifiers are already hashed."""

    visit_id: str
    source_uuid: str
    household_id: str | None = None
    month_index: int = 0
    visit_date: date | None = None
    is_synthetic: bool = False
    grant_amount_lkr: float | None = None
    grant_spent_lkr: float | None = None
    monthly_expenditure_lkr: float | None = None
    grant_remaining_lkr: float | None = None
    grant_use_status: str | None = None
    grant_used_per_plan: bool | None = None
    disaster_impact_reported: bool | None = None
    livelihood_difficulty_reported: bool | None = None
    business_running: bool | None = None
    profit: bool | None = None
    borrowed_money: bool | None = None
    revenue_mid_lkr: float | None = None
    problem_count: float | None = None
    record_keeping_level: float | None = None
    saved_amount_lkr: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Visit":
        """Build a visit from a database or importer row."""
        values = dict(row)
        if isinstance(values.get("visit_date"), str):
            values["visit_date"] = date.fromisoformat(values["visit_date"])
        values.pop("created_at", None)
        return cls(**{k: v for k, v in values.items() if k in cls.__dataclass_fields__})


@dataclass(slots=True)
class CheckResult:
    code: str
    value: CheckValue
    reason: str
    measures: dict[str, Any] = field(default_factory=dict)
    severity: str = "info"


@dataclass(slots=True)
class BlockResult:
    name: str
    checks: list[CheckResult] = field(default_factory=list)


@dataclass(slots=True)
class FinancialReport:
    visit_id: str
    run_id: str | None
    reliability_level: str | None
    confidence: float | None
    risk: float | None
    rule_score: float | None
    model_score: float | None
    level: str | None
    data_origin: str
    blocks: list[BlockResult]
    flags: list[CheckResult]
    unknowns: list[CheckResult]
    raw_features: dict[str, Any]
    model_name: str | None = None
    model_created: str | None = None
    artifact_versions: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-safe report data without PII."""
        def check(item: CheckResult) -> dict[str, Any]:
            return {"code": item.code, "value": item.value, "reason": item.reason, "measures": item.measures, "severity": item.severity}
        return {
            "visit_id": self.visit_id,
            "run_id": self.run_id,
            "reliability_level": self.reliability_level,
            "confidence": self.confidence,
            "risk": self.risk,
            "rule_score": self.rule_score,
            "model_score": self.model_score,
            "level": self.level,
            "data_origin": self.data_origin,
            "blocks": [{"name": b.name, "checks": [check(c) for c in b.checks]} for b in self.blocks],
            "flags": [check(c) for c in self.flags],
            "unknowns": [check(c) for c in self.unknowns],
            "raw_features": self.raw_features,
            "model_name": self.model_name,
            "model_created": self.model_created,
            "artifact_versions": self.artifact_versions,
            "created_at": self.created_at,
        }

    def as_text(self) -> str:
        """Return a readable report without identifiers beyond visit_id."""
        lines = ["# Financial risk report", f"Visit: {self.visit_id}", f"Level: {self.level or 'Unknown'}", f"Risk: {self.risk!r}", "", "## Flags"]
        lines.extend(f"- {x.code}: {x.reason}" for x in self.flags) or lines.append("- None")
        lines.append("\n## Unknowns")
        lines.extend(f"- {x.code}: {x.reason}" for x in self.unknowns) or lines.append("- None")
        lines.append("\n## Measures")
        lines.extend(f"- {key}: {value!r}" for key, value in self.raw_features.items())
        return "\n".join(lines) + "\n"
