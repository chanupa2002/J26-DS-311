"""Monitoring-photo persistence for the database-backed duplicate flow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .duplicate_index import IndexEntry


@dataclass(slots=True)
class MonitoringRecord:
    """One persisted monitoring photo and its comparison features."""

    entry: IndexEntry
    division: str | None = None
    livelihood_category: str | None = None
    image_reference: str | None = None
    image_bytes: bytes | None = None


class MonitoringRepository(ABC):
    """Repository interface used by the duplicate and progress stages."""

    @abstractmethod
    def same_household(self, household_id: str, before_month: str | None = None) -> list[MonitoringRecord]:
        """Return earlier records for one household."""

    @abstractmethod
    def same_category(self, category: str, before_month: str | None = None) -> list[MonitoringRecord]:
        """Return earlier records in the same livelihood category."""

    @abstractmethod
    def latest_previous(self, household_id: str, before_month: str) -> MonitoringRecord | None:
        """Return the latest earlier record for a household."""

    @abstractmethod
    def save(self, record: MonitoringRecord) -> None:
        """Persist one monitoring record after validation."""

    @abstractmethod
    def read_image(self, record: MonitoringRecord) -> bytes | None:
        """Read image bytes for month-to-month comparison."""


def _month_key(value: str) -> str:
    return value.replace("/", "-")


class InMemoryMonitoringRepository(MonitoringRepository):
    """Deterministic repository for tests and local development."""

    def __init__(self) -> None:
        self.records: list[MonitoringRecord] = []

    def same_household(self, household_id: str, before_month: str | None = None) -> list[MonitoringRecord]:
        return [record for record in self.records if record.entry.household_id == household_id and (before_month is None or _month_key(record.entry.month) < _month_key(before_month))]

    def same_category(self, category: str, before_month: str | None = None) -> list[MonitoringRecord]:
        return [record for record in self.records if record.livelihood_category == category and (before_month is None or _month_key(record.entry.month) < _month_key(before_month))]

    def latest_previous(self, household_id: str, before_month: str) -> MonitoringRecord | None:
        records = self.same_household(household_id, before_month)
        return max(records, key=lambda record: _month_key(record.entry.month), default=None)

    def save(self, record: MonitoringRecord) -> None:
        self.records.append(record)

    def read_image(self, record: MonitoringRecord) -> bytes | None:
        return record.image_bytes


class SupabaseMonitoringRepository(MonitoringRepository):
    """Supabase implementation using the shared application client."""

    def __init__(self, client: Any | None = None, table: str = "evidence_trust_monitoring") -> None:
        if client is None:
            from app.core.database import get_supabase
            client = get_supabase()
        self.client = client
        self.table = table

    @staticmethod
    def _record(row: dict[str, Any]) -> MonitoringRecord:
        month = row.get("monitoring_month") or row.get("month")
        if not month:
            raise ValueError("monitoring record has no month")
        entry = IndexEntry(row["household_id"], str(month), row["content_hash"], row.get("phash", ""), row.get("dhash", ""), [float(value) for value in row.get("embedding", [])], row.get("keypoints", []), row.get("descriptors", []), tuple(row["image_size"]) if row.get("image_size") else None, row.get("feature_metadata", {}))
        return MonitoringRecord(entry, row.get("division"), row.get("livelihood_category"), row.get("image_reference"))

    def _query(self, column: str, value: str, before_month: str | None) -> list[MonitoringRecord]:
        query = self.client.table(self.table).select("*").eq(column, value)
        if before_month:
            query = query.lt("monitoring_month_key", _month_key(before_month))
        response = query.execute()
        return [self._record(row) for row in (response.data or [])]

    def same_household(self, household_id: str, before_month: str | None = None) -> list[MonitoringRecord]:
        return self._query("household_id", household_id, before_month)

    def same_category(self, category: str, before_month: str | None = None) -> list[MonitoringRecord]:
        return self._query("livelihood_category", category, before_month)

    def latest_previous(self, household_id: str, before_month: str) -> MonitoringRecord | None:
        records = self.same_household(household_id, before_month)
        return max(records, key=lambda record: _month_key(record.entry.month), default=None)

    def read_image(self, record: MonitoringRecord) -> bytes | None:
        if record.image_bytes:
            return record.image_bytes
        if not record.image_reference:
            return None
        bucket = getattr(self, "bucket", "evidence-trust-monitoring")
        response = self.client.storage.from_(bucket).download(record.image_reference)
        return bytes(response) if response else None

    def save(self, record: MonitoringRecord) -> None:
        entry = record.entry
        image_reference = record.image_reference
        if record.image_bytes:
            self.bucket = getattr(self, "bucket", "evidence-trust-monitoring")
            image_reference = f"{entry.household_id}/{entry.month}/{entry.content_hash}.jpg"
            self.client.storage.from_(self.bucket).upload(image_reference, record.image_bytes, {"content-type": "image/jpeg", "upsert": "true"})
        payload = {"household_id": entry.household_id, "division": record.division, "livelihood_category": record.livelihood_category, "monitoring_year": int(entry.month[:4]) if entry.month[:4].isdigit() else None, "monitoring_month": entry.month, "monitoring_month_key": _month_key(entry.month), "image_reference": image_reference, "content_hash": entry.content_hash, "phash": entry.phash, "dhash": entry.dhash, "embedding": entry.embedding, "keypoints": entry.keypoints, "descriptors": entry.descriptors, "image_size": list(entry.image_size) if entry.image_size else None, "feature_metadata": entry.feature_metadata, "created_at": datetime.now(timezone.utc).isoformat()}
        self.client.table(self.table).insert(payload).execute()
