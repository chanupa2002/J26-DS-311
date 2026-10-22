"""Persistence adapters for visits and financial reports."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from .contracts import FinancialReport, Visit


class FinancialRepository(ABC):
    """Repository interface used by the pipeline and API."""

    @abstractmethod
    def get_visit(self, visit_id: str) -> Visit | None: ...

    @abstractmethod
    def get_history(self, visit: Visit) -> list[Visit]: ...

    @abstractmethod
    def save_run(self, report: FinancialReport) -> str: ...

    @abstractmethod
    def upsert_visit(self, visit: Visit) -> None: ...


class InMemoryFinancialRepository(FinancialRepository):
    """Deterministic repository for tests and offline development."""

    def __init__(self) -> None:
        self.visits: dict[str, Visit] = {}
        self.runs: dict[str, FinancialReport] = {}

    def get_visit(self, visit_id: str) -> Visit | None:
        return self.visits.get(visit_id)

    def get_history(self, visit: Visit) -> list[Visit]:
        return sorted([x for x in self.visits.values() if visit.household_id and x.household_id == visit.household_id and x.month_index < visit.month_index], key=lambda x: x.month_index)

    def save_run(self, report: FinancialReport) -> str:
        run_id = report.run_id or str(uuid4())
        report.run_id = run_id
        self.runs[run_id] = report
        return run_id

    def upsert_visit(self, visit: Visit) -> None:
        existing = next((key for key, value in self.visits.items() if value.source_uuid == visit.source_uuid), None)
        if existing and existing != visit.visit_id:
            del self.visits[existing]
        self.visits[visit.visit_id] = visit

    def get_run(self, run_id: str) -> FinancialReport | None:
        return self.runs.get(run_id)


class SupabaseFinancialRepository(FinancialRepository):
    """Supabase implementation using the shared application client."""

    def __init__(self, client: Any | None = None) -> None:
        if client is None:
            from app.core.database import get_supabase
            client = get_supabase()
        self.client = client

    def get_visit(self, visit_id: str) -> Visit | None:
        response = self.client.table("evidence_trust_monitoring_visits").select("*").eq("visit_id", visit_id).limit(1).execute()
        return Visit.from_row(response.data[0]) if response.data else None

    def get_history(self, visit: Visit) -> list[Visit]:
        if not visit.household_id: return []
        response = self.client.table("evidence_trust_monitoring_visits").select("*").eq("household_id", visit.household_id).lt("month_index", visit.month_index).order("month_index").execute()
        return [Visit.from_row(row) for row in (response.data or [])]

    def upsert_visit(self, visit: Visit) -> None:
        data = {k: v for k, v in visit.__dict__.items()} if hasattr(visit, "__dict__") else {name: getattr(visit, name) for name in visit.__dataclass_fields__ if name != "created_at"}
        data["visit_date"] = data["visit_date"].isoformat() if data.get("visit_date") else None
        data["created_at"] = visit.created_at.isoformat()
        self.client.table("evidence_trust_monitoring_visits").upsert(data, on_conflict="source_uuid").execute()

    def save_run(self, report: FinancialReport) -> str:
        run_id = report.run_id or str(uuid4())
        report.run_id = run_id
        payload = {"run_id": run_id, "visit_id": report.visit_id, "model_name": report.model_name, "model_created": report.model_created, "artifact_versions": report.artifact_versions, "reliability_level": report.reliability_level, "confidence": report.confidence, "risk": report.risk, "rule_score": report.rule_score, "model_score": report.model_score, "level": report.level, "data_origin": report.data_origin, "report_json": report.as_dict(), "report_text": report.as_text()}
        self.client.table("evidence_trust_financial_runs").insert(payload).execute()
        flags = [{"run_id": run_id, "block": block.name, "code": check.code, "value": check.value, "severity": check.severity, "reason": check.reason, "measures": check.measures} for block in report.blocks for check in block.checks]
        if flags: self.client.table("evidence_trust_financial_flags").insert(flags).execute()
        return run_id

    def get_run(self, run_id: str) -> FinancialReport | None:
        response = self.client.table("evidence_trust_financial_runs").select("report_json").eq("run_id", run_id).limit(1).execute()
        return response.data[0].get("report_json") if response.data else None
