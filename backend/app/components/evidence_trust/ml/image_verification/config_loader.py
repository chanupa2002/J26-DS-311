"""Configuration loading and stable hashing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "pipeline": {
        "max_concurrency": 4,
        "stop_on_unusable": False,
        "blocks": [
            {"name": "quality", "enabled": True},
            {"name": "duplicate", "enabled": True},
            {"name": "similarity_change", "enabled": True},
            {"name": "authenticity", "enabled": True},
            {"name": "category_match", "enabled": True},
        ],
    },
    "image": {"fixed_longest_side": 512},
}


def load_config(path: str | Path | None = None) -> tuple[dict[str, Any], str]:
    """Load YAML configuration and return it with a hash of its bytes."""
    config_path = Path(path) if path else Path(__file__).parent / "config" / "image_verification.yaml"
    raw = config_path.read_bytes()
    try:
        import yaml  # type: ignore

        config = yaml.safe_load(raw) or {}
    except ImportError:
        # The checked-in config is also valid JSON, allowing basic use before
        # optional image-verification dependencies are installed.
        config = json.loads(raw.decode("utf-8"))
    return config, hashlib.sha256(raw).hexdigest()
