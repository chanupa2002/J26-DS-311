"""Cached, version-aware loading of grant_risk.joblib."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)
REQUIRED_KEYS = {"pipeline", "model_name", "features", "train_scores", "rule_weight", "thresholds", "rules", "max_points", "versions", "created"}


@lru_cache(maxsize=1)
def load_artifact(path: str | None = None) -> dict[str, Any]:
    """Load and validate the artifact once; version mismatches only warn."""
    default_path = Path(__file__).parent / "model_artifacts" / "grant_risk.joblib"
    artifact_path = Path(path or os.getenv("GRANT_RISK_ARTIFACT_PATH", default_path))
    if not artifact_path.exists():
        raise FileNotFoundError(f"Grant risk model artifact not found: {artifact_path}. Set GRANT_RISK_ARTIFACT_PATH.")
    import joblib
    artifact = joblib.load(artifact_path)
    missing = REQUIRED_KEYS - set(artifact)
    if missing: raise ValueError(f"Grant risk artifact is missing required keys: {', '.join(sorted(missing))}")
    installed: dict[str, str] = {}
    for name in ("sklearn", "numpy", "pandas", "joblib"):
        try:
            module = __import__(name)
            installed[name] = getattr(module, "__version__", "unknown")
        except ImportError: pass
    for name, saved in artifact.get("versions", {}).items():
        if name in installed and str(saved) != str(installed[name]):
            LOGGER.warning("Grant risk artifact %s version mismatch: saved=%s installed=%s", name, saved, installed[name])
    return artifact
