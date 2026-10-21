"""Tests for SHAP explanations (service, explainer and POST /api/risk/explain)."""

import sys

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.components.market_risk import services
from app.components.market_risk.ml import explainer, loader
from app.components.market_risk.ml.sustain_predict import validate_input
from app.components.market_risk.router import router
from app.components.market_risk.tests.conftest import build_features

app = FastAPI()
app.include_router(router)
client = TestClient(app)

TOLERANCE = 1e-6


def _explain(features, horizon="both", top_k=5):
    response = client.post(
        "/api/risk/explain",
        json={"horizon": horizon, "top_k": top_k, "features": features},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _assert_no_internals(response):
    assert "Traceback" not in response.text
    assert "ml/models" not in response.text
    assert str(loader.ML_DIR) not in response.text
    assert ".joblib" not in response.text


@pytest.mark.parametrize(
    ("horizon", "expected"),
    [("3M", ["3M"]), ("6M", ["6M"]), ("both", ["3M", "6M"])],
)
def test_explain_endpoint_horizons(features, horizon, expected):
    body = _explain(features, horizon)

    assert body["horizon"] == horizon
    assert [e["horizon"] for e in body["explanations"]] == expected
    assert "not real-world causes" in body["note"] and "NOT_READY" in body["note"]
    for explanation in body["explanations"]:
        assert explanation["explained_class"] == explanation["predicted_risk"]
        assert explanation["model_name"] == f"SUSTAIN_Model_{explanation['horizon']}"
        assert explanation["model_status"] == "NOT_READY"
        assert explanation["deployment_reason"]
        assert 0.0 <= explanation["high_risk_probability"] <= 1.0


@pytest.mark.parametrize("horizon", loader.HORIZONS)
def test_response_is_additive(features, horizon):
    explanation = _explain(features, horizon)["explanations"][0]

    total = (
        explanation["base_value"]
        + sum(f["contribution"] for f in explanation["top_factors"])
        + explanation["other_features_contribution"]
    )
    assert abs(total - explanation["probability"]) < TOLERANCE


@pytest.mark.parametrize("horizon", loader.HORIZONS)
def test_explainer_is_additive_for_every_class(metadata, horizon):
    features = build_features(metadata, F_Age=None, F_Mkt_Pressure_t=None, F_District=None)
    model, meta = loader.load_model(horizon)
    X, _ = validate_input(pd.DataFrame([features], columns=meta["feature_names_in_order"]), meta)

    result = explainer.explain(horizon, X)

    assert result["contributions"].shape == (53, 3)
    totals = result["base_values"] + result["contributions"].sum(axis=0)
    assert np.allclose(totals, model.predict_proba(X)[0], atol=TOLERANCE, rtol=0)
    assert result["additivity_difference"] < TOLERANCE


@pytest.mark.parametrize("top_k", [1, 5, 20])
def test_factors_have_top_k_items_sorted_by_abs_contribution(features, top_k):
    for explanation in _explain(features, "both", top_k)["explanations"]:
        for factors in (explanation["top_factors"], explanation["high_risk_factors"]):
            assert len(factors) == top_k
            sizes = [abs(f["contribution"]) for f in factors]
            assert sizes == sorted(sizes, reverse=True)


def test_every_factor_is_one_of_the_53_features(metadata, features):
    allowed = set(metadata["feature_names_in_order"])

    for explanation in _explain(features, "both", 20)["explanations"]:
        for factors in (explanation["top_factors"], explanation["high_risk_factors"]):
            names = [f["feature"] for f in factors]
            assert set(names) <= allowed
            assert len(names) == len(set(names))
            for factor in factors:
                assert factor["direction"] in {"increases risk", "decreases risk"}
                assert factor["label"]
                assert factor["value"] == features[factor["feature"]]


def test_transformed_columns_map_to_original_features(metadata):
    model, _ = loader.load_model("3M")
    names = model[:-1].get_feature_names_out()

    mapped = {explainer.original_feature(n, metadata["categorical_features"]) for n in names}

    assert mapped == set(metadata["feature_names_in_order"])
    with pytest.raises(explainer.ExplanationError):
        explainer.original_feature("other__x", metadata["categorical_features"])


def _assert_same(a, b):
    """Equal structure and text; floats equal up to parallel-summation noise (~1e-16)."""
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            _assert_same(a[key], b[key])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            _assert_same(x, y)
    elif isinstance(a, float):
        assert a == pytest.approx(b, abs=1e-9)
    else:
        assert a == b


def test_upper_case_category_gives_same_explanation_as_trained_level(metadata):
    converted = _explain(build_features(metadata, F_Category="TRADE"))
    canonical = _explain(build_features(metadata, F_Category="Trade"))

    _assert_same(converted["explanations"], canonical["explanations"])
    assert "F_Category: converted 'TRADE' -> 'Trade' using category_mapping" in converted["warnings"]


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"F_Category": "Trade", "F_District": "Ampara", "F_No_Profit_Last_Month_t": 1.0, "F_Risk_Signal_Count_t": 2.0},
        {"F_Business_Not_Running_t": 1.0, "F_Risk_Ord_t": 2.0, "F_High_Count_6M_Window": 3.0},
    ],
)
def test_predicted_risk_equals_predict_endpoint(metadata, overrides):
    features = build_features(metadata, **overrides)

    predicted = client.post("/api/risk/predict", json={"horizon": "both", "features": features}).json()
    explained = _explain(features)

    assert [p["predicted_risk"] for p in predicted["predictions"]] == [
        e["predicted_risk"] for e in explained["explanations"]
    ]
    for prediction, explanation in zip(predicted["predictions"], explained["explanations"]):
        assert prediction["probabilities"]["High"] == pytest.approx(explanation["high_risk_probability"], abs=1e-4)


def test_all_null_features_can_be_explained(metadata):
    features = {name: None for name in metadata["feature_names_in_order"]}

    body = _explain(features)

    assert len(body["explanations"]) == 2
    assert any("51 numeric features were null" in w for w in body["warnings"])


def test_service_accepts_a_plain_dict(features):
    result = services.explain_market_risk({"horizon": "3M", "features": features})

    assert [e.horizon for e in result.explanations] == ["3M"]
    assert len(result.explanations[0].top_factors) == 5


@pytest.mark.parametrize(
    ("change", "location"),
    [
        ({"top_k": 0}, ["body", "top_k"]),
        ({"top_k": 21}, ["body", "top_k"]),
        ({"top_k": "abc"}, ["body", "top_k"]),
        ({"horizon": "12M"}, ["body", "horizon"]),
        ({"extra": 1}, ["body", "extra"]),
    ],
)
def test_invalid_request_is_422(features, change, location):
    response = client.post("/api/risk/explain", json={"horizon": "both", "features": features, **change})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == location
    _assert_no_internals(response)


def test_extra_feature_key_is_422(features):
    features["F_Agee"] = 1

    response = client.post("/api/risk/explain", json={"features": features})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "features", "F_Agee"]


def test_missing_model_files_give_503(monkeypatch, tmp_path, reset_loader, features):
    monkeypatch.setattr(loader, "MODELS_DIR", tmp_path)

    response = client.post("/api/risk/explain", json={"features": features})

    assert response.status_code == 503
    assert "model files are missing" in response.json()["detail"]
    _assert_no_internals(response)


def test_sklearn_version_mismatch_gives_503(monkeypatch, reset_loader, features):
    import sklearn

    monkeypatch.setattr(sklearn, "__version__", "0.0.0")

    response = client.post("/api/risk/explain", json={"features": features})

    assert response.status_code == 503
    assert "scikit-learn version mismatch" in response.json()["detail"]
    _assert_no_internals(response)


def test_missing_shap_library_gives_503(monkeypatch, reset_loader, features):
    monkeypatch.setitem(sys.modules, "shap", None)

    response = client.post("/api/risk/explain", json={"features": features})

    assert response.status_code == 503
    assert "SHAP explanation library is not installed" in response.json()["detail"]
    _assert_no_internals(response)


def test_failed_additivity_check_gives_503(monkeypatch, features):
    monkeypatch.setattr(explainer, "ADDITIVITY_TOLERANCE", -1.0)

    with pytest.raises(explainer.ExplanationError, match="additivity"):
        services.explain_market_risk({"features": features})

    response = client.post("/api/risk/explain", json={"features": features})
    assert response.status_code == 503
    assert "consistency check" in response.json()["detail"]
    _assert_no_internals(response)


def test_explainer_is_cached(features):
    _explain(features)
    before = explainer._load_explainer_cached.cache_info()

    _explain(features)

    after = explainer._load_explainer_cached.cache_info()
    assert after.currsize == 2
    assert after.misses == before.misses
