"""YAML configuration loading for financial risk."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path | None = None) -> tuple[dict[str, Any], str]:
    """Load config and return its stable content hash."""
    config_path = Path(path) if path else Path(__file__).parent / "config" / "financial_risk.yaml"
    raw = config_path.read_bytes()
    try:
        import yaml  # type: ignore
        config = yaml.safe_load(raw) or {}
    except ImportError:
        config = json.loads(raw.decode("utf-8"))
    return config, hashlib.sha256(raw).hexdigest()
