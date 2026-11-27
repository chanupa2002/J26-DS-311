"""Officer decisions on recommendations (FR7).

Stored in the Supabase table market_risk_decisions when Supabase is configured and the table
exists (SQL in CONTRACTS_UPDATE.md); otherwise in a local SQLite file,
artifacts_v2/decisions.sqlite3 (git-ignored). Stored: household_key (synthetic SIM-HH-… only),
rule_id, decision, note, planned_visit_date, knowledge_version and created_at – nothing else.
"""

import logging
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from app.components.market_risk.v2 import artifacts

logger = logging.getLogger(__name__)

TABLE = "market_risk_decisions"
SQLITE_FILE = "decisions.sqlite3"
FIELDS = ("household_key", "rule_id", "decision", "note", "planned_visit_date", "knowledge_version", "created_at")
PUBLIC_FIELDS = ("decision", "note", "planned_visit_date", "knowledge_version", "created_at")


class DecisionStoreError(RuntimeError):
    """The decision could not be stored or read. The message is safe to show."""


class Store(Protocol):
    name: str

    def add(self, record: dict[str, Any]) -> None: ...

    def records(self, household_key: str) -> list[dict[str, Any]]: ...


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def latest_by_rule(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Latest decision per rule_id (records in any order)."""
    latest: dict[str, dict[str, Any]] = {}
    for record in sorted(records, key=lambda r: (str(r["created_at"]), r.get("id") or 0)):
        latest[record["rule_id"]] = {name: record.get(name) for name in PUBLIC_FIELDS}
    return latest


class SQLiteStore:
    name = "sqlite"

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        with closing(self._connect()) as db, db:
            db.execute(
                f"CREATE TABLE IF NOT EXISTS {TABLE} ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, household_key TEXT NOT NULL, rule_id TEXT NOT NULL, "
                "decision TEXT NOT NULL, note TEXT, planned_visit_date TEXT, knowledge_version TEXT NOT NULL, "
                "created_at TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def add(self, record: dict[str, Any]) -> None:
        with self._lock, closing(self._connect()) as db, db:
            db.execute(
                f"INSERT INTO {TABLE} ({', '.join(FIELDS)}) VALUES ({', '.join('?' for _ in FIELDS)})",
                [record[name] for name in FIELDS],
            )

    def records(self, household_key: str) -> list[dict[str, Any]]:
        with self._lock, closing(self._connect()) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(f"SELECT * FROM {TABLE} WHERE household_key = ?", (household_key,)).fetchall()
        return [dict(row) for row in rows]


class SupabaseStore:
    name = "supabase"

    def __init__(self, client: Any):
        self.client = client
        self.client.table(TABLE).select("id").limit(1).execute()  # fails if the table is missing

    def add(self, record: dict[str, Any]) -> None:
        self.client.table(TABLE).insert({name: record[name] for name in FIELDS}).execute()

    def records(self, household_key: str) -> list[dict[str, Any]]:
        response = self.client.table(TABLE).select("*").eq("household_key", household_key).execute()
        return list(response.data or [])


_store: Store | None = None
_store_lock = threading.Lock()


def _open_default() -> Store:
    from app.core.config import settings  # read-only use of the shared settings

    if settings.supabase_url and settings.supabase_key:
        try:
            from app.core.database import get_supabase

            return SupabaseStore(get_supabase())
        except Exception as exc:  # type only: messages may contain connection details
            logger.warning("market_risk v2: Supabase table %s not available (%s); using local SQLite",
                           TABLE, type(exc).__name__)
    return SQLiteStore(artifacts.artifacts_dir() / SQLITE_FILE)


def get_store() -> Store:
    global _store
    with _store_lock:
        if _store is None:
            _store = _open_default()
        return _store


def set_store(store: Store | None) -> None:
    """Use this store (tests), or None to choose again on next use."""
    global _store
    with _store_lock:
        _store = store


def save(record: dict[str, Any]) -> dict[str, Any]:
    record = {**record, "created_at": now()}
    try:
        get_store().add(record)
    except Exception as exc:
        logger.error("market_risk v2: decision not stored (%s)", type(exc).__name__)
        raise DecisionStoreError("The decision could not be stored.") from None
    return {name: record.get(name) for name in PUBLIC_FIELDS}


def latest(household_key: str) -> dict[str, dict[str, Any]]:
    try:
        return latest_by_rule(get_store().records(household_key))
    except Exception as exc:
        logger.error("market_risk v2: decisions not readable (%s)", type(exc).__name__)
        raise DecisionStoreError("Saved decisions could not be read.") from None
