"""Market and macro features per (category, month) from ml/market_context.json.

The 8 F_Mkt_* features depend only on (category, month) and the 5 F_Macro_*
features only on month, so a field officer cannot know them. The lookup file is
built by ml/training/build_market_context.py with the same join and formulas as
training, and holds aggregated public indicators only (no household data).
Standard library only; the file is read once and cached.
"""

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

LOOKUP_PATH = Path(__file__).parent / "market_context.json"


@lru_cache(maxsize=1)
def _load_cached() -> dict[str, Any]:
    if not LOOKUP_PATH.is_file():
        raise FileNotFoundError("market_risk lookup file is missing: ml/market_context.json")
    with LOOKUP_PATH.open(encoding="utf-8") as lookup_file:
        return json.load(lookup_file)


def load_lookup() -> dict[str, Any]:
    """Return a copy of the lookup file."""
    return copy.deepcopy(_load_cached())


def resolve_category(category: str) -> tuple[str, str] | None:
    """Trained level (any case) or upper-case survey name -> (level, category key); None if unknown."""
    lookup = _load_cached()
    text = str(category).strip()
    levels = {level.casefold(): level for level in lookup["level_keys"]}
    if text.casefold() in levels:
        level = levels[text.casefold()]
        return level, lookup["level_keys"][level]
    key = text.upper()
    if key in lookup["category_keys"]:
        return lookup["category_keys"][key], key
    return None


def context_values(category_key: str, month: str) -> dict[str, Any] | None:
    """The 13 F_* values for (category key, month); None if the month is not in the data."""
    lookup = _load_cached()
    if month not in lookup["macro"]:
        return None
    return {**lookup["market"][category_key][month], **lookup["macro"][month]}


def clear_cache() -> None:
    """Forget the loaded lookup (used by tests)."""
    _load_cached.cache_clear()
