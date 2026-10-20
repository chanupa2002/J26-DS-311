"""API tests for the market-risk endpoints."""

import pytest
import sklearn
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.components.market_risk.ml import loader
from app.components.market_risk.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _assert_no_internals(response):
    assert "Traceback" not in response.text
    assert "ml/models" not in response.text
    assert str(loader.ML_DIR) not in response.text
    assert ".joblib" not in response.text


def test_health_endpoint():
    response = client.get("/api/risk/health")

    assert response.status_code == 200
    assert response.json() == {"component": "market_risk", "status": "ok"}


def test_predict_endpoint(features):
    response = client.post("/api/risk/predict", json={"horizon": "both", "features": features})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"horizon", "predictions", "warnings", "placeholder"}
    assert body["placeholder"] is False
    assert [p["horizon"] for p in body["predictions"]] == ["3M", "6M"]
    for prediction in body["predictions"]:
        assert prediction["predicted_risk"] in {"Low", "Medium", "High"}
        assert prediction["model_status"] == "NOT_READY"
        assert prediction["deployment_reason"]


def test_predict_horizon_defaults_to_both(features):
    response = client.post("/api/risk/predict", json={"features": features})

    assert response.status_code == 200
    assert response.json()["horizon"] == "both"


def test_predict_extra_key_is_422(features):
    features["F_Agee"] = 1

    response = client.post("/api/risk/predict", json={"horizon": "3M", "features": features})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "features", "F_Agee"]


def test_predict_missing_key_is_422(features):
    features.pop("F_Age")

    response = client.post("/api/risk/predict", json={"horizon": "3M", "features": features})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "features", "F_Age"]


def test_predict_bad_horizon_is_422(features):
    response = client.post("/api/risk/predict", json={"horizon": "12M", "features": features})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "horizon"]


def test_predict_non_numeric_value_is_422(features):
    features["F_Age"] = "abc"

    response = client.post("/api/risk/predict", json={"horizon": "3M", "features": features})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "features", "F_Age"]


def test_model_info_endpoint():
    response = client.get("/api/risk/model-info")

    assert response.status_code == 200
    body = response.json()
    assert [m["horizon"] for m in body["models"]] == ["3M", "6M"]
    assert all(m["model_status"] == "NOT_READY" for m in body["models"])
    assert len(body["features"]) == 53
    assert set(body["categorical_levels"]) == {"F_Category", "F_District"}


def test_model_info_single_horizon():
    response = client.get("/api/risk/model-info", params={"horizon": "6M"})

    assert response.status_code == 200
    assert [m["horizon"] for m in response.json()["models"]] == ["6M"]


def test_model_info_bad_horizon_is_422():
    response = client.get("/api/risk/model-info", params={"horizon": "12M"})

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [("post", "/api/risk/predict"), ("get", "/api/risk/model-info")],
)
def test_missing_model_files_give_503(
    monkeypatch, tmp_path, reset_loader, features, method, path
):
    monkeypatch.setattr(loader, "MODELS_DIR", tmp_path)

    if method == "post":
        response = client.post(path, json={"horizon": "both", "features": features})
    else:
        response = client.get(path)

    assert response.status_code == 503
    assert "model files are missing" in response.json()["detail"]
    _assert_no_internals(response)


def test_sklearn_version_mismatch_gives_503(monkeypatch, reset_loader, features):
    monkeypatch.setattr(sklearn, "__version__", "0.0.0")

    response = client.post("/api/risk/predict", json={"horizon": "3M", "features": features})

    assert response.status_code == 503
    assert "scikit-learn version mismatch" in response.json()["detail"]
    _assert_no_internals(response)


def test_error_responses_do_not_leak_internals(features):
    features["F_Agee"] = 1

    _assert_no_internals(client.post("/api/risk/predict", json={"features": features}))
    _assert_no_internals(client.post("/api/risk/predict", json={"features": {}}))
