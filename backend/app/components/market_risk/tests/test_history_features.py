"""Tests for compute_history_features and POST /api/risk/history-features (inline data only)."""

import copy

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.components.market_risk import services
from app.components.market_risk.ml.training import check_history_features as chf
from app.components.market_risk.ml.training import features as fx
from app.components.market_risk.schemas import HistoryFeatures, HistoryFeaturesRequest
from app.components.market_risk.tests.test_training_features import _panel
from app.main import app

client = TestClient(app)
URL = "/api/risk/history-features"
EXAMPLE = HistoryFeaturesRequest.model_config["json_schema_extra"]["examples"][0]


def _visit(month, running=1, profit=1, progressing=1, stress=0):
    return {"month": month, "business_running": running, "profit_last_month": profit,
            "progressing_well": progressing, "market_stress": stress}


def _current(visit_date="2026-06-15", grant_date=None, running=1, profit=1, progressing=1, stress=0):
    return {"visit_date": visit_date, "business_running": running, "profit_last_month": profit,
            "progressing_well": progressing, "market_stress": stress, "grant_date": grant_date}


# ------------------------------------------------- same as the training code ----
def _toy_training_panel():
    """Two households with gaps, blanks and grant dates; risk classes from the training rule."""
    rows = []
    visits = {
        "HH-001": [("2026-01", 0, 1, 0, 0, None), ("2026-02", 0, 1, 1, np.nan, "2026-01-20"),
                   ("2026-04", 0, np.nan, 0, 1, None), ("2026-05", 1, 0, 0, 0, None), ("2026-09", 0, 0, 0, 0, None)],
        "HH-002": [("2026-03", np.nan, 0, 0, 0, None), ("2026-04", 0, 1, np.nan, 1, "2026-05-02"),
                   ("2026-06", 0, 1, 1, 1, None)],
    }
    for household, items in visits.items():
        for month, not_running, no_profit, not_progressing, stress, grant in items:
            rows.append({
                "household_id": household, "month": month, "Month_Ord": pd.Period(month, freq="M").ordinal,
                "T_Business_Not_Running": not_running, "T_No_Profit_Last_Month": no_profit,
                "T_Not_Progressing_Well": not_progressing, "T_Market_Stress_Any": stress,
                "visit_date": pd.Timestamp(f"{month}-11"), "grant_date": pd.Timestamp(grant) if grant else pd.NaT,
            })
    panel = _panel(rows)
    panel["Risk_Ord_t"], _, _ = fx.risk_rule_a(panel[fx.T_COLS])
    return panel


def test_service_reproduces_the_training_history_features():
    panel = _toy_training_panel()

    result = chf.check(panel, fx.build_features(panel))

    assert result["rows_checked"] == len(panel) == 8
    assert result["rows_all_14_equal"] == 8
    assert set(result["per_feature_match_rate"].values()) == {1.0}
    assert result["rows_grant_after_visit_sent_as_null"] == 1  # HH-002 2026-04: grant on 05-02


def test_check_reports_a_mismatch():
    panel = _toy_training_panel()
    features = fx.build_features(panel)
    features.loc[features.index[3], "F_Tenure_Months"] += 1

    result = chf.check(panel, features)

    assert result["rows_all_14_equal"] == 7
    assert result["per_feature_match_rate"]["F_Tenure_Months"] < 1.0


def test_first_visit_equals_the_training_values_for_a_first_visit():
    panel = _panel([{"household_id": "HH-009", "month": "2026-03", "Month_Ord": pd.Period("2026-03", freq="M").ordinal,
                     "T_No_Profit_Last_Month": 1.0, "Risk_Ord_t": 1.0, "visit_date": pd.Timestamp("2026-03-08"),
                     "grant_date": pd.Timestamp("2026-02-01")}])
    expected = fx.build_features(panel).iloc[0]

    got = services.compute_history_features({
        "current_visit": _current("2026-03-08", "2026-02-01", profit=0), "previous_visits": [],
    }).features.model_dump()

    for name in fx.HISTORY_FEATURES:
        assert (got[name] is None and np.isnan(expected[name])) or got[name] == float(expected[name]), name
    assert got["F_N_Prior_Visits"] == 0 and got["F_Tenure_Months"] == 0 and got["F_Prev_Risk_Ord"] is None


def test_feature_list_matches_the_training_list():
    assert list(HistoryFeatures.model_fields) == fx.HISTORY_FEATURES


# ----------------------------------------------------------------- endpoint ----
def test_example_request():
    response = client.post(URL, json=EXAMPLE)

    assert response.status_code == 200
    body = response.json()
    f = body["features"]
    assert body["month"] == "2026-04"
    assert [v["month"] for v in body["visits"]] == ["2026-02", "2026-03", "2026-04"]
    assert [v["risk_class"] for v in body["visits"]] == ["Low", "High", "Medium"]
    assert f["F_Months_Since_Prev_Visit"] == 1 and f["F_Prev_Risk_Ord"] == 2 and f["F_Risk_Change_vs_Prev"] == -1
    assert f["F_Tenure_Months"] == 2 and f["F_N_Prior_Visits"] == 2
    assert f["F_Risk_Mean_3M_Window"] == 1.0 and f["F_High_Count_6M_Window"] == 1
    assert f["F_NoProfit_Rate_3M_Window"] == pytest.approx(2 / 3)
    assert f["F_Months_Since_Grant"] == pytest.approx(82 / 30.44)  # 2026-01-20 -> 2026-04-12


def test_previous_visit_order_does_not_matter():
    reversed_request = {**EXAMPLE, "previous_visits": list(reversed(EXAMPLE["previous_visits"]))}

    assert client.post(URL, json=reversed_request).json() == client.post(URL, json=EXAMPLE).json()


def test_twelve_previous_visits_are_allowed():
    months = [str(pd.Period("2025-04", freq="M") + i) for i in range(12)]

    response = client.post(URL, json={"current_visit": _current("2026-04-03"), "previous_visits": [_visit(m) for m in months]})

    assert response.status_code == 200
    assert response.json()["features"]["F_N_Prior_Visits"] == 12


def _with(**changes):
    request = copy.deepcopy(EXAMPLE)
    for key, value in changes.items():
        if key == "current":
            request["current_visit"].update(value)
        else:
            request[key] = value
    return request


@pytest.mark.parametrize(
    "request_body",
    [
        _with(current={"visit_date": "2026-04-31"}),
        _with(current={"visit_date": "12/04/2026"}),
        _with(current={"grant_date": "2026-04-13"}),  # after visit_date
        _with(previous_visits=[_visit("2026-13")]),
        _with(previous_visits=[_visit("2026-02"), _visit("2026-02")]),  # duplicate months
        _with(previous_visits=[_visit("2026-04")]),  # same month as visit_date
        _with(previous_visits=[_visit("2026-05")]),  # after the current visit
        _with(previous_visits=[_visit(str(pd.Period("2025-03", freq="M") + i)) for i in range(13)]),  # 13 visits
        _with(current={"household_id": "HH-001"}),  # no IDs: extra keys are rejected
        _with(previous_visits=[{**_visit("2026-02"), "name": "x"}]),
        _with(current={"profit_last_month": 2}),
        {"previous_visits": []},
    ],
)
def test_bad_input_returns_422(request_body):
    assert client.post(URL, json=request_body).status_code == 422


def test_service_raises_validation_error_for_direct_callers():
    with pytest.raises(ValidationError):
        services.compute_history_features(_with(previous_visits=[_visit("2026-04")]))
