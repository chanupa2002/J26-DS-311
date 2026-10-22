"""Import monitoring_visits_clean.csv without printing beneficiary rows."""

from __future__ import annotations

import argparse
import csv
import logging
from datetime import date
from pathlib import Path
from uuid import uuid4

from ..contracts import Visit
from ..repository import SupabaseFinancialRepository

LOGGER = logging.getLogger(__name__)


def _bool(value: str | None) -> bool | None:
    if value is None or value == "": return None
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _number(value: str | None) -> float | None:
    return None if value is None or value == "" else float(value)


def import_csv(path: str | Path, repository) -> int:
    """Upsert CSV visits and return a count, never logging row contents."""
    count = 0
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            source_uuid = row.get("source_uuid") or str(uuid4())
            household = row.get("household_id") or None
            if "is_synthetic" in row and row["is_synthetic"] != "": synthetic = bool(_bool(row["is_synthetic"]))
            else:
                synthetic = household is not None
                if count == 0: LOGGER.warning("is_synthetic column absent; inferring synthetic=%s when household_id is present", synthetic)
            visit = Visit(
                visit_id=row.get("visit_id") or str(uuid4()), source_uuid=source_uuid, household_id=household,
                month_index=int(row.get("month_index") or 0), visit_date=date.fromisoformat(row["visit_date"]) if row.get("visit_date") else None,
                is_synthetic=synthetic, grant_spent_lkr=_number(row.get("grant_spent_lkr")), grant_remaining_lkr=_number(row.get("grant_remaining_lkr")),
                grant_use_status=row.get("grant_use_status") or None, grant_used_per_plan=_bool(row.get("grant_used_per_plan")),
                disaster_impact_reported=_bool(row.get("disaster_impact_reported")), livelihood_difficulty_reported=_bool(row.get("livelihood_difficulty_reported")),
                business_running=_bool(row.get("business_running")), profit=_bool(row.get("profit")), borrowed_money=_bool(row.get("borrowed_money")),
                revenue_mid_lkr=_number(row.get("revenue_mid_lkr")), problem_count=_number(row.get("problem_count")), record_keeping_level=_number(row.get("record_keeping_level")), saved_amount_lkr=_number(row.get("saved_amount_lkr")),
            )
            repository.upsert_visit(visit)
            count += 1
    LOGGER.info("Imported %d monitoring visits", count)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Import monitoring visits into Supabase")
    parser.add_argument("path", help="Path to monitoring_visits_clean.csv")
    args = parser.parse_args()
    import_csv(args.path, SupabaseFinancialRepository())


if __name__ == "__main__": main()
