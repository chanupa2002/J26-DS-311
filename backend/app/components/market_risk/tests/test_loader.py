"""Tests for the cached 3M/6M model loader."""

import shutil

import pytest
import sklearn

from app.components.market_risk.ml import loader


@pytest.mark.parametrize("horizon", loader.HORIZONS)
def test_model_loads_and_is_cached(horizon):
    model, metadata = loader.load_model(horizon)
    again, _ = loader.load_model(horizon)

    assert again is model
    assert hasattr(model, "predict_proba")
    assert metadata["model_name"] == f"SUSTAIN_Model_{horizon}"
    assert list(model.feature_names_in_) == metadata["feature_names_in_order"]
    assert len(model.classes_) == len(metadata["classes"]) == 3


def test_metadata_is_consistent_between_horizons():
    meta_3m = loader.load_metadata("3M")
    meta_6m = loader.load_metadata("6M")

    assert meta_3m["feature_names_in_order"] == meta_6m["feature_names_in_order"]
    assert meta_3m["categorical_levels"] == meta_6m["categorical_levels"]
    assert meta_3m["classes"] == meta_6m["classes"] == ["Low", "Medium", "High"]

    order = meta_3m["feature_names_in_order"]
    assert len(order) == 53
    assert meta_3m["numeric_features"] + meta_3m["categorical_features"] == order
    schema_names = [item["name"] for item in loader.load_feature_schema("3M")]
    assert schema_names == order


def test_metadata_copy_cannot_change_the_cache():
    loader.load_metadata("3M")["feature_names_in_order"].clear()

    assert len(loader.load_metadata("3M")["feature_names_in_order"]) == 53


@pytest.mark.parametrize("horizon", loader.HORIZONS)
def test_model_status_is_exposed(horizon):
    status = loader.get_model_status(horizon)

    assert status["model_status"] == "NOT_READY"
    assert status["deployment_reason"]


def test_unknown_horizon_raises_value_error():
    with pytest.raises(ValueError, match="Unknown horizon"):
        loader.load_model("12M")


def test_missing_model_file_raises(monkeypatch, tmp_path, reset_loader):
    (tmp_path / "3M").mkdir()
    shutil.copy(loader.ML_DIR / "models" / "3M" / "metadata.json", tmp_path / "3M")
    monkeypatch.setattr(loader, "MODELS_DIR", tmp_path)

    with pytest.raises(FileNotFoundError, match="model.joblib"):
        loader.load_model("3M")


def test_missing_metadata_file_raises(monkeypatch, tmp_path, reset_loader):
    monkeypatch.setattr(loader, "MODELS_DIR", tmp_path)

    with pytest.raises(FileNotFoundError, match="metadata.json"):
        loader.load_metadata("6M")


def test_sklearn_version_mismatch_raises(monkeypatch, reset_loader):
    monkeypatch.setattr(sklearn, "__version__", "0.0.0")

    with pytest.raises(RuntimeError, match="requires scikit-learn 1.6.1"):
        loader.load_model("3M")
