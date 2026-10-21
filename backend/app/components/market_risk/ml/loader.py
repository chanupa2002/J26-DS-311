"""Load and cache the SUSTAIN 3M/6M market-risk models and their metadata.

Each horizon has its own folder under ml/models/ with model.joblib,
metadata.json and feature_schema.json. Files are loaded on first use, not when
the server starts, and then kept in memory.

Both models are currently deployment_status "NOT_READY"; callers must pass
model_status and deployment_reason on to the user (see get_model_status).

For LOCAL side-by-side testing only, the environment variable
MARKET_RISK_MODELS_DIR can point to another folder with the same layout (for
example the retraining candidate outside the repo). Default: ml/models/.
"""

import copy
import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

ML_DIR = Path(__file__).parent
MODELS_DIR = Path(os.environ.get("MARKET_RISK_MODELS_DIR") or ML_DIR / "models").expanduser()
HORIZONS = ("3M", "6M")
MODEL_FILENAME = "model.joblib"
METADATA_FILENAME = "metadata.json"
FEATURE_SCHEMA_FILENAME = "feature_schema.json"

logger = logging.getLogger(__name__)


def _horizon_dir(horizon: str) -> Path:
    if horizon not in HORIZONS:
        allowed = ", ".join(HORIZONS)
        raise ValueError(f"Unknown horizon {horizon!r}. Allowed: {allowed}")
    return MODELS_DIR / horizon


def _required_file(horizon: str, filename: str) -> Path:
    path = _horizon_dir(horizon) / filename
    if not path.is_file():
        raise FileNotFoundError(
            f"market_risk {horizon} model artifact is missing: "
            f"ml/models/{horizon}/{filename}"
        )
    return path


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


@lru_cache(maxsize=None)
def _load_metadata_cached(horizon: str) -> dict[str, Any]:
    metadata = _read_json(_required_file(horizon, METADATA_FILENAME))
    for key in (
        "feature_names_in_order",
        "numeric_features",
        "categorical_features",
        "categorical_levels",
        "classes",
        "deployment_status",
    ):
        if key not in metadata:
            raise ValueError(
                f"market_risk {horizon} metadata.json is missing key: {key}"
            )
    return metadata


@lru_cache(maxsize=None)
def _load_feature_schema_cached(horizon: str) -> list[dict[str, Any]]:
    schema = _read_json(_required_file(horizon, FEATURE_SCHEMA_FILENAME))
    return schema["features"]


def load_metadata(horizon: str) -> dict[str, Any]:
    """Return a copy of metadata.json for a horizon. Does not import sklearn."""
    return copy.deepcopy(_load_metadata_cached(horizon))


def load_feature_schema(horizon: str) -> list[dict[str, Any]]:
    """Return a copy of the feature list (name, type, description) for a horizon."""
    return copy.deepcopy(_load_feature_schema_cached(horizon))


def get_model_status(horizon: str) -> dict[str, str]:
    """Return model_status and deployment_reason. NOT_READY is never hidden."""
    metadata = _load_metadata_cached(horizon)
    return {
        "model_status": str(metadata["deployment_status"]),
        "deployment_reason": str(metadata.get("deployment_reason") or ""),
    }


@lru_cache(maxsize=None)
def _load_model_cached(horizon: str) -> Any:
    model_path = _required_file(horizon, MODEL_FILENAME)
    metadata = _load_metadata_cached(horizon)

    import joblib
    import sklearn

    required_version = str(
        metadata.get("software_versions", {}).get("scikit-learn", "")
    ).strip()
    if sklearn.__version__ != required_version:
        raise RuntimeError(
            f"market_risk {horizon} model requires scikit-learn "
            f"{required_version or '(not recorded)'}, but {sklearn.__version__} "
            "is installed. Install the pinned version or retrain the model with "
            "the installed version."
        )

    model = joblib.load(model_path)

    expected_features = list(metadata["feature_names_in_order"])
    model_features = list(getattr(model, "feature_names_in_", expected_features))
    if model_features != expected_features:
        raise RuntimeError(
            f"market_risk {horizon} model.joblib features do not match "
            "metadata.json feature_names_in_order."
        )
    n_classes = len(getattr(model, "classes_", metadata["classes"]))
    if n_classes != len(metadata["classes"]):
        raise RuntimeError(
            f"market_risk {horizon} model has {n_classes} classes but "
            f"metadata.json lists {len(metadata['classes'])}."
        )

    status = get_model_status(horizon)
    if status["model_status"] != "READY":
        logger.warning(
            "market_risk %s model status is %s: %s",
            horizon,
            status["model_status"],
            status["deployment_reason"],
        )
    return model


def load_model(horizon: str) -> tuple[Any, dict[str, Any]]:
    """Load the fitted pipeline once and return (model, metadata copy).

    Raises:
        ValueError: unknown horizon or incomplete metadata.json.
        FileNotFoundError: model.joblib or metadata.json is missing.
        RuntimeError: installed scikit-learn differs from the training version,
            or the model does not match its metadata.
    """
    return _load_model_cached(horizon), load_metadata(horizon)


def clear_cache() -> None:
    """Forget loaded models and metadata (used by tests)."""
    _load_model_cached.cache_clear()
    _load_metadata_cached.cache_clear()
    _load_feature_schema_cached.cache_clear()
