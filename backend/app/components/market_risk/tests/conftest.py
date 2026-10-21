"""Shared fixtures for market_risk tests. Inputs are built inline from metadata.json."""

import pytest

from app.components.market_risk.ml import explainer, loader


def build_features(metadata: dict, **overrides) -> dict:
    """One valid row: numerics 0.0, categoricals = first trained level."""
    features = {
        name: (
            metadata["categorical_levels"][name][0]
            if name in metadata["categorical_features"]
            else 0.0
        )
        for name in metadata["feature_names_in_order"]
    }
    features.update(overrides)
    return features


@pytest.fixture
def metadata() -> dict:
    return loader.load_metadata("3M")


@pytest.fixture
def features(metadata) -> dict:
    return build_features(metadata)


@pytest.fixture
def reset_loader():
    """Start and finish with an empty loader cache (for tests that monkeypatch)."""
    loader.clear_cache()
    explainer.clear_cache()
    yield
    loader.clear_cache()
    explainer.clear_cache()
