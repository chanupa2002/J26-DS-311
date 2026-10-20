"""Tests for the public market_risk service functions."""

import joblib
import pytest
from pydantic import ValidationError

from app.components.market_risk import services
from app.components.market_risk.ml import loader
from app.components.market_risk.schemas import MarketRiskFeatures, PredictRequest
from app.components.market_risk.tests.conftest import build_features

# validate_input also emits these as UserWarnings; tests check them in result.warnings.
pytestmark = pytest.mark.filterwarnings("ignore:.*unseen categories:UserWarning")


def _predict(features, horizon="both"):
    return services.predict_market_risk(
        PredictRequest(horizon=horizon, features=features)
    )


def test_schema_fields_match_metadata_order():
    for horizon in loader.HORIZONS:
        order = loader.load_metadata(horizon)["feature_names_in_order"]
        assert list(MarketRiskFeatures.model_fields) == order


@pytest.mark.parametrize(
    ("horizon", "expected"),
    [("3M", ["3M"]), ("6M", ["6M"]), ("both", ["3M", "6M"])],
)
def test_predict_horizons(features, horizon, expected):
    result = _predict(features, horizon)

    assert result.horizon == horizon
    assert result.placeholder is False
    assert [p.horizon for p in result.predictions] == expected
    for prediction in result.predictions:
        probabilities = prediction.probabilities.model_dump()
        assert set(probabilities) == {"Low", "Medium", "High"}
        assert all(0.0 <= p <= 1.0 for p in probabilities.values())
        assert sum(probabilities.values()) == pytest.approx(1.0, abs=1e-3)
        assert prediction.predicted_risk == max(probabilities, key=probabilities.get)
        assert prediction.model_name == f"SUSTAIN_Model_{prediction.horizon}"
        assert prediction.model_status == "NOT_READY"
        assert prediction.deployment_reason


def test_predict_accepts_a_plain_dict(features):
    result = services.predict_market_risk({"horizon": "3M", "features": features})

    assert [p.horizon for p in result.predictions] == ["3M"]


def test_predict_dict_with_missing_key_is_rejected(features):
    features.pop("F_Age")

    with pytest.raises(ValidationError):
        services.predict_market_risk({"horizon": "3M", "features": features})


def test_complete_row_has_no_warnings(features):
    assert _predict(features).warnings == []


def test_unknown_category_and_district_give_warnings(metadata):
    features = build_features(metadata, F_Category="Space Tourism", F_District="Galle")

    result = _predict(features)

    assert len(result.predictions) == 2
    assert any("F_Category" in w and "Space Tourism" in w for w in result.warnings)
    assert any("F_District" in w and "Galle" in w for w in result.warnings)
    assert len(result.warnings) == len(set(result.warnings))


def test_upper_case_survey_category_is_converted(metadata):
    converted = _predict(build_features(metadata, F_Category="TRADE"), "3M")
    canonical = _predict(build_features(metadata, F_Category="Trade"), "3M")

    assert "F_Category: converted 'TRADE' -> 'Trade' using category_mapping" in converted.warnings
    assert converted.predictions[0].probabilities == canonical.predictions[0].probabilities
    assert canonical.warnings == []


def test_category_not_in_mapping_stays_unknown(metadata):
    result = _predict(build_features(metadata, F_Category="TRANSPORT & LOGISTICS"), "6M")

    assert not any("converted" in w for w in result.warnings)
    assert any("unseen categories" in w and "TRANSPORT" in w for w in result.warnings)


def test_all_null_features_still_predict(metadata):
    features = {name: None for name in metadata["feature_names_in_order"]}

    result = _predict(features)

    assert len(result.predictions) == 2
    assert all(p.model_status == "NOT_READY" for p in result.predictions)
    assert any("51 numeric features were null" in w for w in result.warnings)
    assert "F_Category: null -> encoded as all-zero" in result.warnings
    assert "F_District: null -> encoded as all-zero" in result.warnings


def test_get_model_info_does_not_load_model_files(monkeypatch, reset_loader):
    def fail_load(*args, **kwargs):
        raise AssertionError("get_model_info must not load model.joblib")

    monkeypatch.setattr(joblib, "load", fail_load)

    info = services.get_model_info()

    assert loader._load_model_cached.cache_info().currsize == 0
    assert [m.horizon for m in info.models] == ["3M", "6M"]
    assert all(m.model_status == "NOT_READY" and m.deployment_reason for m in info.models)
    assert [f.name for f in info.features] == loader.load_metadata("3M")["feature_names_in_order"]
    assert set(info.categorical_levels) == {"F_Category", "F_District"}


def test_get_model_info_single_horizon():
    info = services.get_model_info("6M")

    assert [m.horizon for m in info.models] == ["6M"]
    assert info.models[0].horizon_months == 6
