"""Category-photo manifest validation and source-photo splitting."""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = {"file", "category", "source_url", "licence", "provenance"}


def read_category_manifest(path: str | Path) -> list[dict[str, str]]:
    """Read a category manifest and reject unsafe training rows."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if rows and not REQUIRED_COLUMNS.issubset(rows[0]):
        raise ValueError(f"manifest must contain: {', '.join(sorted(REQUIRED_COLUMNS))}")
    for row in rows:
        if row.get("provenance") not in {"web", "field"}:
            raise ValueError("provenance must be web or field")
        if not row.get("category"):
            raise ValueError("category is required")
    return rows


def deduplicate_manifest(rows: list[dict[str, str]], root: str | Path) -> list[dict[str, str]]:
    """Remove exact reposts before splitting, without modifying source files."""
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for row in rows:
        path = Path(root) / row["file"]
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        if digest not in seen:
            seen.add(digest)
            result.append(row)
    return result


def split_by_source_photo(rows: list[dict[str, str]], test_field_only: bool = True) -> dict[str, list[dict[str, str]]]:
    """Group rows by source photo so variants cannot straddle splits."""
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = row.get("source_photo") or row["file"]
        groups[key].append(row)
    ordered = list(groups.values())
    test = [row for group in ordered[-max(1, len(ordered) // 5):] for row in group]
    if test_field_only:
        test.extend(row for row in rows if row.get("provenance") == "field")
    test_ids = {id(row) for row in test}
    train = [row for row in rows if id(row) not in test_ids and row.get("provenance") != "field"]
    return {"train": train, "test": test}
