"""Tests for rule-based current-risk identification (SUSTAIN-HH-Risk-Rule v1.0)."""

import itertools

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.components.market_risk import services
from app.components.market_risk.ml import loader
from app.components.market_risk.router import IDENTIFY_EXAMPLE_RESPONSE, router
from app.components.market_risk.schemas import IdentifyRequest

app = FastAPI()
app.include_router(router)
client = TestClient(app)

KEYS = (
    "business_not_running",
    "no_profit_last_month",
    "not_progressing_well",
    "market_stress_any",
)


def _signals(values) -> dict:
    return dict(zip(KEYS, values))


# (values for KEYS, risk_class, risk_ord, signal_count, unknown_count, decision reason,
#  best_case_class, worst_case_class)
CASES = {
    "all 0": ((0, 0, 0, 0), "Low", 0, 0, 0, "Business running and all three signals answered No -> Low", "Low", "Low"),
    "one signal": ((0, 1, 0, 0), "Medium", 1, 1, 0, "Exactly one risk signal -> Medium", "Medium", "Medium"),
    "two signals": ((0, 1, 0, 1), "High", 2, 2, 0, "2 or more risk signals -> High", "High", "High"),
    "three signals": ((0, 1, 1, 1), "High", 2, 3, 0, "2 or more risk signals -> High", "High", "High"),
    "business not running": ((1, 0, 0, 0), "High", 2, 0, 0, "Business not running -> High", "High", "High"),
    "business not running + blanks": ((1, None, None, None), "High", 2, 0, 3, "Business not running -> High", "High", "High"),
    "business null, signals 0": ((None, 0, 0, 0), "Unassigned", None, 0, 0, "Business status not answered -> Unassigned", "Low", "High"),
    "business null, one signal": ((None, 1, 0, 0), "Unassigned", None, 1, 0, "Business status not answered -> Unassigned", "Medium", "High"),
    "business null, two signals (notebook)": ((None, 1, 1, 0), "High", 2, 2, 0, "2 or more risk signals -> High", "High", "High"),
    "blank changes class (0,0,blank)": ((0, 0, 0, None), "Unassigned", None, 0, 1, "Blank answers could change the class -> Unassigned", "Low", "Medium"),
    "blank changes class (1,0,blank)": ((0, 1, 0, None), "Unassigned", None, 1, 1, "Blank answers could change the class -> Unassigned", "Medium", "High"),
    "blank does not change (1,1,blank)": ((0, 1, 1, None), "High", 2, 2, 1, "2 or more risk signals -> High", "High", "High"),
    "all signals blank": ((0, None, None, None), "Unassigned", None, 0, 3, "Blank answers could change the class -> Unassigned", "Low", "High"),
}


def _check(result: dict, case) -> None:
    _, risk_class, risk_ord, signal_count, unknown_count, decision, best, worst = case
    assert result["risk_class"] == risk_class
    assert result["risk_ord"] == risk_ord
    assert result["signal_count"] == signal_count
    assert result["unknown_count"] == unknown_count
    assert decision in result["reasons"]
    assert len(result["reasons"]) == len(set(result["reasons"]))
    assert result["rule_version"] == services.RULE_VERSION

    assert result["best_case_class"] == best
    assert result["worst_case_class"] == worst
    assert result["possible_range"] == (best if best == worst else f"{best}-{worst}")
    assert result["follow_up_needed"] is (risk_class == "Unassigned")
    if risk_class == "Unassigned":
        assert best != worst
        assert result["reasons"][-1] == (
            f"Could be up to {worst} if blank answers are Yes; follow-up visit recommended"
        )
    else:
        assert best == worst == risk_class
        assert result["reasons"][-1] == decision
        assert not any("follow-up" in reason for reason in result["reasons"])


@pytest.mark.parametrize("case", CASES.values(), ids=CASES.keys())
def test_identify_service_cases(case):
    result = services.identify_current_risk(_signals(case[0]))

    _check(result.model_dump(), case)


@pytest.mark.parametrize("case", CASES.values(), ids=CASES.keys())
def test_identify_endpoint_cases(case):
    response = client.post("/api/risk/identify", json=_signals(case[0]))

    assert response.status_code == 200
    _check(response.json(), case)


def test_rule_version_matches_model_metadata():
    for horizon in loader.HORIZONS:
        assert services.RULE_VERSION == loader.load_metadata(horizon)["target_generation_method"]


def test_reasons_name_the_signals_in_plain_english():
    result = services.identify_current_risk(_signals((None, 1, 0, None)))

    assert result.reasons == [
        "Business status not answered",
        "No profit last month",
        "Not answered: market stress",
        "Blank answers could change the class -> Unassigned",
        "Could be up to High if blank answers are Yes; follow-up visit recommended",
    ]


@pytest.mark.parametrize(
    ("values", "best", "worst", "possible_range"),
    [
        ((0, 1, 0, None), "Medium", "High", "Medium-High"),
        ((0, 0, 0, None), "Low", "Medium", "Low-Medium"),
        ((None, 0, 0, 0), "Low", "High", "Low-High"),
    ],
)
def test_unassigned_range_and_follow_up(values, best, worst, possible_range):
    for result in (
        services.identify_current_risk(_signals(values)).model_dump(),
        client.post("/api/risk/identify", json=_signals(values)).json(),
    ):
        assert result["risk_class"] == "Unassigned"
        assert result["best_case_class"] == best
        assert result["worst_case_class"] == worst
        assert result["possible_range"] == possible_range
        assert result["follow_up_needed"] is True


def _notebook_risk_rule(rows: list[tuple]) -> list[str]:
    """SUSTAIN risk_rule variant A, copied from notebook section 12 (cell 49)."""
    classes = ["Low", "Medium", "High"]
    df = pd.DataFrame(
        rows,
        columns=["T_Business_Not_Running", "T_No_Profit_Last_Month", "T_Not_Progressing_Well", "T_Market_Stress_Any"],
        dtype=float,
    )
    bnr = df["T_Business_Not_Running"]
    S = df[["T_No_Profit_Last_Month", "T_Not_Progressing_Well", "T_Market_Stress_Any"]]
    hi = 2
    npos = (S == 1).sum(axis=1); nunk = S.isna().sum(axis=1)
    def cls(n): return np.where(n >= hi, 2, np.where(n >= 1, 1, 0))
    lo_c, hi_c = cls(npos), cls(npos + nunk)
    out = np.where(lo_c == hi_c, lo_c, -1).astype(float)
    out = np.where(bnr == 1, 2, out); out = np.where(bnr.isna() & (out < 2), -1, out)
    return ["Unassigned" if o < 0 else classes[int(o)] for o in out]


ALL_COMBINATIONS = list(itertools.product([0, 1, None], repeat=4))


def test_risk_class_matches_notebook_on_all_81_combinations():
    expected = _notebook_risk_rule(ALL_COMBINATIONS)

    actual = [services.identify_current_risk(_signals(v)).risk_class for v in ALL_COMBINATIONS]

    assert len(ALL_COMBINATIONS) == 81
    assert actual == expected


def test_best_and_worst_match_notebook_with_blanks_filled_on_all_81_combinations():
    """best = notebook class with every blank 0; worst = with every blank 1."""
    fill = lambda values, x: tuple(x if v is None else v for v in values)
    best_expected = _notebook_risk_rule([fill(v, 0) for v in ALL_COMBINATIONS])
    worst_expected = _notebook_risk_rule([fill(v, 1) for v in ALL_COMBINATIONS])

    for values, best, worst in zip(ALL_COMBINATIONS, best_expected, worst_expected):
        result = services.identify_current_risk(_signals(values))
        assert (result.best_case_class, result.worst_case_class) == (best, worst), values


def test_router_example_matches_service_output():
    example_request = IdentifyRequest.model_json_schema()["examples"][0]

    assert services.identify_current_risk(example_request).model_dump() == IDENTIFY_EXAMPLE_RESPONSE


def test_identify_accepts_request_model():
    request = IdentifyRequest(**_signals((0, 1, 1, 0)))

    assert services.identify_current_risk(request).risk_class == "High"


# Agreed behaviour: JSON true/false and 1.0/0.0 are accepted as 1/0.
@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((True, False, False, False), "High"),
        ((False, True, False, False), "Medium"),
        ((0.0, 1.0, 1.0, 0.0), "High"),
        ((0.0, 0.0, 0.0, 0.0), "Low"),
    ],
)
def test_bool_and_float_values_are_accepted_as_0_1(values, expected):
    assert services.identify_current_risk(_signals(values)).risk_class == expected

    response = client.post("/api/risk/identify", json=_signals(values))
    assert response.status_code == 200
    assert response.json()["risk_class"] == expected


INVALID = {
    "extra key": ({**_signals((0, 0, 0, 0)), "revenue_lowest_band": 1}, "revenue_lowest_band"),
    "missing key": (dict(zip(KEYS[:3], (0, 0, 0))), "market_stress_any"),
    "value 5": (_signals((5, 0, 0, 0)), "business_not_running"),
    "value 'abc'": (_signals((0, "abc", 0, 0)), "no_profit_last_month"),
    "value 0.5": (_signals((0, 0, 0.5, 0)), "not_progressing_well"),
}


@pytest.mark.parametrize(("payload", "field"), INVALID.values(), ids=INVALID.keys())
def test_identify_service_rejects_invalid_input(payload, field):
    with pytest.raises(ValidationError) as error:
        services.identify_current_risk(payload)

    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize(("payload", "field"), INVALID.values(), ids=INVALID.keys())
def test_identify_endpoint_rejects_invalid_input_with_422(payload, field):
    response = client.post("/api/risk/identify", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]
    assert "Traceback" not in response.text
