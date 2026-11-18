"""v2 endpoint tests with FastAPI TestClient. All request data is synthetic."""

import logging

import pandas as pd
import pytest
import sklearn.base
from fastapi.testclient import TestClient

from app.components.market_risk.v2 import artifacts
from app.components.market_risk.v2.schemas import EXAMPLE_VISIT, PreviousVisit, VisitRequest
from app.main import app

BASE = "/api/risk/v2"
client = TestClient(app)
ENDPOINTS = ("/risk/households", "/risk/household/SIM-HH-001", "/market/districts", "/model/evidence")


def real_visit(**values) -> dict:
    body = {key: value for key, value in EXAMPLE_VISIT.items() if key != "household_key"}
    return {**body, "is_synthetic": False, **values}


@pytest.fixture
def needs_artifacts():
    if artifacts.missing_files():
        pytest.skip("v2 artifacts are not on this machine (they are git-ignored)")


@pytest.fixture
def fresh_cache():
    artifacts.clear_cache()
    yield
    artifacts.clear_cache()


def test_synthetic_visit_has_full_response(needs_artifacts):
    response = client.post(f"{BASE}/risk/visit", json=EXAMPLE_VISIT)
    assert response.status_code == 200
    body = response.json()
    assert body["is_synthetic"] is True
    assert body["model_version"] == "v2"
    assert body["note"] is None
    assert body["current_risk"]["risk_class"] == "High"
    assert set(body["predictions"]) == {"3M", "6M"}
    assert isinstance(body["predictions"]["3M"]["alert"], bool)
    assert body["predictions"]["6M"]["alert"] is None
    assert body["predictions"]["6M"]["reliability_note"]
    assert body["market"]["level"] in {"Normal", "Moderate", "High", None}


def test_shap_returns_five_readable_factors_that_fit_the_probability(needs_artifacts):
    body = client.post(f"{BASE}/risk/visit", json=EXAMPLE_VISIT).json()
    factors = body["shap_top_factors"]
    assert len(factors) == 5
    sizes = [abs(factor["contribution"]) for factor in factors]
    assert sizes == sorted(sizes, reverse=True)
    groups = {"Business", "Household shock", "History", "Market", "Current risk"}
    for factor in factors:
        assert factor["group"] in groups
        assert factor["label"] != factor["feature"]
        assert factor["value"]


def stored_visit_request(index: int = 2) -> tuple[dict, list[dict]]:
    """A stored synthetic visit as a request, plus that household's earlier visits."""
    store = artifacts.load_bundle().store_visits
    visits = store[store.household_key == "SIM-HH-001"].sort_values("monitoring_period")
    assert len(visits) > index + 1, "the household needs later visits for this test"
    fields = VisitRequest.model_fields.keys() - {"previous_visits"}
    clean = lambda row, names: {
        name: (None if pd.isna(row[name]) else row[name].item() if hasattr(row[name], "item") else row[name])
        for name in names
    }
    numeric = lambda record: {
        key: int(value) if isinstance(value, float) else value for key, value in record.items()
    }
    body = numeric(clean(visits.iloc[index], [name for name in fields if name in visits.columns]))
    earlier_fields = list(PreviousVisit.model_fields)
    earlier = [numeric(clean(row, earlier_fields)) for _, row in visits.iloc[:index].iterrows()]
    return body, earlier


def test_score_uses_only_earlier_stored_visits(needs_artifacts):
    body, earlier = stored_visit_request()
    timeline = client.get(f"{BASE}/risk/household/SIM-HH-001").json()["timeline"]
    assert timeline[-1]["monitoring_period"] > body["monitoring_period"]
    expected = next(p for p in timeline if p["monitoring_period"] == body["monitoring_period"])

    from_store = client.post(f"{BASE}/risk/visit", json=body).json()
    explicit = client.post(f"{BASE}/risk/visit", json={**body, "previous_visits": earlier}).json()
    assert from_store["predictions"]["3M"]["p_high"] == expected["p_high_3m"]
    assert from_store["predictions"] == explicit["predictions"]
    assert from_store["shap_top_factors"] == explicit["shap_top_factors"]


def test_openapi_lists_v2_paths():
    paths = client.get("/openapi.json").json()["paths"]
    assert f"{BASE}/risk/visit" in paths
    assert f"{BASE}/model/evidence" in paths
    assert "/v2/risk/visit" not in paths


def test_real_visit_is_indicative_and_not_logged(needs_artifacts, caplog):
    marker = "Ratnapura"
    with caplog.at_level(logging.DEBUG):
        response = client.post(f"{BASE}/risk/visit", json=real_visit(district=marker))
    assert response.status_code == 200
    body = response.json()
    assert body["is_synthetic"] is False
    assert body["note"] == "indicative - no history"
    assert body["household_key"] is None
    assert marker not in caplog.text


@pytest.mark.parametrize("extra", [{"household_key": "SIM-HH-001"}, {"previous_visits": []}])
def test_real_visit_cannot_use_history(extra):
    assert client.post(f"{BASE}/risk/visit", json=real_visit(**extra)).status_code == 422


def test_synthetic_visit_needs_household_key():
    body = {key: value for key, value in EXAMPLE_VISIT.items() if key != "household_key"}
    assert client.post(f"{BASE}/risk/visit", json=body).status_code == 422


@pytest.mark.parametrize("month", ["2026-06", "2026-07"])
def test_previous_visit_must_be_earlier(month):
    body = {**EXAMPLE_VISIT, "previous_visits": [{"monitoring_period": month}]}
    assert client.post(f"{BASE}/risk/visit", json=body).status_code == 422


def test_unknown_field_is_rejected():
    assert client.post(f"{BASE}/risk/visit", json={**EXAMPLE_VISIT, "nic": "x"}).status_code == 422


@pytest.mark.parametrize("field", ["district", "category"])
def test_unknown_district_or_category_is_rejected(needs_artifacts, field):
    assert client.post(f"{BASE}/risk/visit", json={**EXAMPLE_VISIT, field: "Nowhere"}).status_code == 422


def test_month_after_market_data_returns_503(needs_artifacts):
    for response in (
        client.post(f"{BASE}/risk/visit", json={**EXAMPLE_VISIT, "monitoring_period": "2026-10"}),
        client.get(f"{BASE}/risk/households", params={"month": "2026-10"}),
        client.get(f"{BASE}/market/districts", params={"month": "2026-10"}),
    ):
        assert response.status_code == 503
        assert "2026-09" in response.json()["detail"]


def test_household_list_is_synthetic_only(needs_artifacts):
    response = client.get(f"{BASE}/risk/households", params={"month": "2026-03"})
    assert response.status_code == 200
    body = response.json()
    assert body["is_synthetic"] is True
    assert body["count"] == len(body["households"]) > 0
    assert all(row["household_key"].startswith("SIM-HH-") and row["is_synthetic"] for row in body["households"])


def test_household_detail_has_ordered_timeline(needs_artifacts):
    body = client.get(f"{BASE}/risk/household/SIM-HH-001").json()
    months = [point["monitoring_period"] for point in body["timeline"]]
    assert months == sorted(months)
    assert body["latest_visit"]["monitoring_period"] == months[-1]
    assert len(body["latest_visit"]["shap_top_factors"]) == 5


def test_unknown_household_and_non_synthetic_key(needs_artifacts):
    assert client.get(f"{BASE}/risk/household/SIM-HH-NOPE").status_code == 404
    assert client.get(f"{BASE}/risk/household/REAL-1").status_code == 422


def test_market_table_has_25_districts_by_9_categories(needs_artifacts):
    body = client.get(f"{BASE}/market/districts", params={"month": "2026-09"}).json()
    assert body["count"] == 225
    assert len({row["district"] for row in body["rows"]}) == 25
    assert len({row["category"] for row in body["rows"]}) == 9
    assert body["is_synthetic"] is False


def test_evidence_reports_persistence_and_limitations(needs_artifacts):
    body = client.get(f"{BASE}/model/evidence").json()
    assert body["model_version"] == "v2"
    assert body["alert_thresholds"]["6M"] is None
    assert len(body["comparisons"]) == 6
    assert any("6M" in row["name"] and not row["model_better"] for row in body["comparisons"])
    assert body["limitations"]
    text = str(body)
    assert "SIM-HH-" not in text and "household_key" not in text


def test_missing_artifacts_return_503(monkeypatch, tmp_path, fresh_cache):
    monkeypatch.setenv("MARKET_RISK_ARTIFACTS_DIR", str(tmp_path))
    artifacts.clear_cache()
    for path in ENDPOINTS:
        response = client.get(f"{BASE}{path}")
        assert response.status_code == 503
        assert "missing" in response.json()["detail"]
        assert str(tmp_path) not in response.json()["detail"]
    assert client.post(f"{BASE}/risk/visit", json=EXAMPLE_VISIT).status_code == 503


def test_scikit_learn_version_mismatch_returns_503(needs_artifacts, monkeypatch, fresh_cache, caplog):
    monkeypatch.setattr(sklearn.base, "__version__", "0.0.test")
    artifacts.clear_cache()
    with caplog.at_level(logging.ERROR):
        response = client.get(f"{BASE}/model/evidence")
    assert response.status_code == 503
    assert "scikit-learn" in response.json()["detail"]
    assert "scikit-learn" in caplog.text


def test_startup_check_runs_and_v1_keeps_working(monkeypatch, tmp_path, fresh_cache, caplog):
    monkeypatch.setenv("MARKET_RISK_ARTIFACTS_DIR", str(tmp_path))
    artifacts.clear_cache()
    with caplog.at_level(logging.ERROR), TestClient(app) as started:
        assert started.get("/api/risk/health").status_code == 200
        assert started.get(f"{BASE}/model/evidence").status_code == 503
    assert "v2 endpoints will return 503" in caplog.text
