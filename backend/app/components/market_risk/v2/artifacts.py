"""Load and check the v2 artifacts (git-ignored, under an NDA where they hold visits).

The folder comes from MARKET_RISK_ARTIFACTS_DIR, default market_risk/artifacts_v2/.
Everything is loaded once. Real visits are dropped as soon as the visits file is read,
so they never enter the household store. Messages never contain paths or row values.
"""

import json
import logging
import os
import re
import threading
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.components.market_risk.v2 import pipeline, transitions

logger = logging.getLogger(__name__)

MODEL_NAMES = ("3M_warning", "6M_warning", "3M_classes", "6M_classes")
VISITS_FILE = "SUSTAIN_Cleaned_Monitoring.csv"
MARKET_FILE = "SUSTAIN_District_Category_Market_Risk_25.csv"
OPL_FILE = "DCS_OPL_2026.csv"
MACRO_FILE = "macro_anomalies_monthly.csv"
EVIDENCE_FILE = "model_evidence.json"
META_FILE = "model_meta.json"
REGISTER_FILE = "threshold_register.json"
REQUIRED_FILES = (
    META_FILE, REGISTER_FILE, VISITS_FILE, MARKET_FILE, OPL_FILE, MACRO_FILE, EVIDENCE_FILE,
    *(f"model_{name}.joblib" for name in MODEL_NAMES),
)


class ArtifactsUnavailable(RuntimeError):
    """v2 cannot serve. The message is safe to show to API callers."""


@dataclass(frozen=True)
class Bundle:
    meta: dict[str, Any]
    evidence: dict[str, Any]
    models: dict[str, Any]
    explainer_3m: Any
    tables: pipeline.PipelineTables
    revenue_labels: dict[int, str]
    months: list[str]
    districts: list[str]
    categories: list[str]
    training_districts: list[str]
    store_visits: pd.DataFrame  # synthetic households only
    store_features: pd.DataFrame
    store_predictions: pd.DataFrame
    transitions: transitions.Transitions  # estimated from store_features, never typed


_lock = threading.RLock()
_bundle: Bundle | None = None
_failure: ArtifactsUnavailable | None = None


def artifacts_dir() -> Path:
    configured = os.environ.get("MARKET_RISK_ARTIFACTS_DIR")
    return Path(configured).expanduser() if configured else Path(__file__).parents[1] / "artifacts_v2"


def missing_files() -> list[str]:
    folder = artifacts_dir()
    return [name for name in REQUIRED_FILES if not (folder / name).is_file()]


def _load_model(path: Path) -> Any:
    """Load one model, and refuse it if it was saved with another scikit-learn version.

    scikit-learn removes the recorded version while unpickling and reports a difference
    only through InconsistentVersionWarning, so that warning is the check.
    """
    import joblib
    import sklearn
    from sklearn.exceptions import InconsistentVersionWarning

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = joblib.load(path)
    recorded = sorted({
        item.message.original_sklearn_version
        for item in caught
        if issubclass(item.category, InconsistentVersionWarning)
    })
    if recorded:
        raise ArtifactsUnavailable(
            f"{path.name} was saved with scikit-learn {', '.join(recorded)} but "
            f"{sklearn.__version__} is installed. Install the pinned version from requirements.txt."
        )
    return model


def _k_high(register: list[dict]) -> int:
    for entry in register:
        if entry["threshold"].startswith("Risk rule"):
            match = re.search(r"k\s*=\s*(\d+)", entry["value"])
            if match:
                return int(match.group(1))
    raise ArtifactsUnavailable(f"{REGISTER_FILE} has no risk-rule entry.")


def _load() -> Bundle:
    import shap

    folder = artifacts_dir()
    meta = json.loads((folder / META_FILE).read_text(encoding="utf-8"))
    register = json.loads((folder / REGISTER_FILE).read_text(encoding="utf-8"))
    evidence = json.loads((folder / EVIDENCE_FILE).read_text(encoding="utf-8"))

    models = {name: _load_model(folder / f"model_{name}.joblib") for name in MODEL_NAMES}
    for name, model in models.items():
        feature_set = meta["warning_model" if "warning" in name else "classes_model"]["features"]
        if list(model.feature_names_in_) != meta["feature_columns"][feature_set]:
            raise ArtifactsUnavailable(f"model_{name}.joblib does not match {META_FILE}.")

    columns = [*pipeline.VISIT_INPUT_COLUMNS, "revenue_upper_lkr", "revenue_band_label"]
    visits = pd.read_csv(folder / VISITS_FILE, usecols=columns, dtype={"household_key": "string"}, low_memory=False)
    visits = visits[visits.is_synthetic.astype(bool) & visits.household_key.notna()].reset_index(drop=True)
    bands = visits[visits.revenue_band.notna()].drop_duplicates("revenue_band")

    market = pd.read_csv(folder / MARKET_FILE, low_memory=False)
    tables = pipeline.PipelineTables(
        opl=pd.read_csv(folder / OPL_FILE)[["month", "national_opl_lkr"]],
        market=market,
        macro=pd.read_csv(folder / MACRO_FILE),
        revenue_upper={int(r.revenue_band): float(r.revenue_upper_lkr) for r in bands.itertuples()},
        k_high=_k_high(register),
    )
    store_features = pipeline.build_features(visits, tables)
    return Bundle(
        meta=meta,
        evidence=evidence,
        models=models,
        explainer_3m=shap.TreeExplainer(models["3M_warning"][-1]),
        tables=tables,
        revenue_labels={int(r.revenue_band): str(r.revenue_band_label) for r in bands.itertuples()},
        months=sorted(market.month.unique().tolist()),
        districts=sorted(market.district.unique().tolist()),
        categories=sorted(market.category.unique().tolist()),
        training_districts=[
            c[len("district_"):] for c in meta["feature_columns"][meta["classes_model"]["features"]]
            if c.startswith("district_")
        ],
        store_visits=visits,
        store_features=store_features,
        store_predictions=pipeline.predict_visits(store_features, models, meta),
        transitions=transitions.estimate(store_features),
    )


def load_bundle() -> Bundle:
    """Return the loaded artifacts, or raise ArtifactsUnavailable with a safe message."""
    global _bundle, _failure
    with _lock:
        missing = missing_files()
        if missing:
            raise ArtifactsUnavailable(f"Required v2 files are missing: {', '.join(missing)}.")
        if _bundle is not None:
            return _bundle
        if _failure is not None:
            raise _failure
        try:
            _bundle = _load()
        except ArtifactsUnavailable as exc:
            _failure = exc
            logger.error("market_risk v2 disabled: %s", exc)
            raise
        except Exception as exc:  # type only: messages from data libraries can quote values
            logger.error("market_risk v2 disabled: artifacts could not be read (%s)", type(exc).__name__)
            _failure = ArtifactsUnavailable("The v2 artifacts could not be read.")
            raise _failure from None
        return _bundle


def check_on_startup() -> None:
    """Load everything at start-up. A failure is logged and v1 keeps working."""
    try:
        load_bundle()
    except ArtifactsUnavailable as exc:
        logger.error("market_risk v2 endpoints will return 503: %s", exc)


def clear_cache() -> None:
    """Forget loaded artifacts and failures (used by tests)."""
    global _bundle, _failure
    with _lock:
        _bundle = None
        _failure = None
