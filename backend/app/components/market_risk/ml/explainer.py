"""SHAP explanations for the SUSTAIN 3M/6M market-risk models.

One shap.TreeExplainer per horizon is built on the RandomForest step of the
saved pipeline (pipeline[-1]) and applied to data transformed by the
preprocessing step (pipeline[:-1]). Explainers are created on first use and
cached, like the models in loader.py.

The ~94 transformed columns are mapped back to the 53 original features by
summing their contributions (value column + missing indicator, and all one-hot
columns of a categorical feature).
"""

from functools import lru_cache
from typing import Any

import numpy as np

from app.components.market_risk.ml import loader

ADDITIVITY_TOLERANCE = 1e-6
NUM_PREFIX = "num__"
MISSING_PREFIX = "num__missingindicator_"
CAT_PREFIX = "cat__"


def original_feature(transformed_name: str, categorical_features: list[str]) -> str:
    """Map a transformed column name to its original F_* feature."""
    if transformed_name.startswith(MISSING_PREFIX):
        return transformed_name[len(MISSING_PREFIX):]
    if transformed_name.startswith(NUM_PREFIX):
        return transformed_name[len(NUM_PREFIX):]
    if transformed_name.startswith(CAT_PREFIX):
        rest = transformed_name[len(CAT_PREFIX):]
        for name in categorical_features:
            if rest.startswith(name + "_"):
                return name
    raise ValueError(f"Cannot map transformed feature {transformed_name!r} to an input feature")


@lru_cache(maxsize=None)
def _load_explainer_cached(horizon: str) -> tuple[Any, np.ndarray]:
    """Return (TreeExplainer, aggregation matrix of shape (n_transformed, n_original))."""
    import shap

    model, metadata = loader.load_model(horizon)
    preprocess, forest = model[:-1], model[-1]
    explainer = shap.TreeExplainer(forest)

    features = metadata["feature_names_in_order"]
    index = {name: i for i, name in enumerate(features)}
    transformed = preprocess.get_feature_names_out()
    aggregation = np.zeros((len(transformed), len(features)))
    for row, name in enumerate(transformed):
        aggregation[row, index[original_feature(name, metadata["categorical_features"])]] = 1.0
    return explainer, aggregation


def _as_rows_features_classes(shap_values: Any, n_classes: int) -> np.ndarray:
    """Normalise shap output to an array of shape (rows, features, classes)."""
    if isinstance(shap_values, list):
        values = np.stack([np.asarray(v) for v in shap_values], axis=-1)
    else:
        values = np.asarray(shap_values)
    if values.ndim != 3 or values.shape[-1] != n_classes:
        raise RuntimeError(
            f"Unexpected SHAP output shape {values.shape}; expected (rows, features, {n_classes})"
        )
    return values


def explain(horizon: str, X) -> dict[str, Any]:
    """SHAP contributions for one validated input row X (DataFrame in feature order).

    Returns base_values (per class), probabilities (per class) and contributions
    (original features x classes), with labels from metadata["classes"].
    Raises RuntimeError if base value + contributions != model probability.
    """
    model, metadata = loader.load_model(horizon)
    explainer, aggregation = _load_explainer_cached(horizon)
    transformed = model[:-1].transform(X)
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()

    forest = model[-1]
    classes = [metadata["classes"][int(c)] for c in forest.classes_]
    raw = _as_rows_features_classes(explainer.shap_values(transformed), len(classes))
    contributions = aggregation.T @ raw[0]  # (n_original, n_classes)
    base_values = np.broadcast_to(np.asarray(explainer.expected_value, dtype=float), (len(classes),))
    probabilities = forest.predict_proba(transformed)[0]

    difference = float(np.max(np.abs(base_values + contributions.sum(axis=0) - probabilities)))
    if difference >= ADDITIVITY_TOLERANCE:
        raise RuntimeError(
            f"SHAP additivity check failed for market_risk {horizon} model "
            f"(max difference {difference:.2e} >= {ADDITIVITY_TOLERANCE:.0e})."
        )

    return {
        "classes": classes,
        "features": list(metadata["feature_names_in_order"]),
        "base_values": base_values.copy(),
        "probabilities": probabilities,
        "contributions": contributions,
        "additivity_difference": difference,
    }


def clear_cache() -> None:
    """Forget built explainers (used by tests)."""
    _load_explainer_cached.cache_clear()
