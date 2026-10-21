"""Tests for the market-context lookup, get_market_context and GET /api/risk/market-context.

The builder is tested on an inline toy Category_Month_Table; the endpoint uses the
committed ml/market_context.json (aggregated indicators only, no data files read).
"""

import math

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.components.market_risk import services
from app.components.market_risk.ml import loader, market_context
from app.components.market_risk.ml.training import build_market_context as bmc
from app.components.market_risk.ml.training import features as fx
from app.components.market_risk.schemas import MarketContextFeatures
from app.main import app

client = TestClient(app)
URL = "/api/risk/market-context"


# ---------------------------------------------------------------- builder ----
def _toy_category_month():
    base = {column: np.nan for column in fx.MARKET_COLUMNS}
    macro = {
        "2026-01": dict(zip(fx.MACRO_COLUMNS, [2.0, 1.5, 110.0, 100.0, 300.0, 250.0])),
        "2026-02": dict(zip(fx.MACRO_COLUMNS, [2.5, 2.0, 99.0, 110.0, 300.0, 300.0])),
    }
    trade_jan = {**base, "Primary_Pressure_t": 4.0, "Primary_Pressure_t_minus_1": 1.0, "Primary_Volatility_t": 2.0,
                 "Primary_Volatility_t_minus_1": 3.0, "Category_Pressure_Tier_Ord_t": 2.0,
                 "Category_Volatility_Tier_Ord_t": 0.0, "Category_Pressure_Tier_Ord_t_minus_1": 1.0}
    rows = [
        {"Month": "2026-01", "Category_Key": "TRADE", "Row_Basis": "ALL", **trade_jan, **macro["2026-01"]},
        # REAL / SYNTHETIC rows must be ignored for the market values
        {"Month": "2026-01", "Category_Key": "TRADE", "Row_Basis": "REAL", **{**trade_jan, "Primary_Pressure_t": 99.0}, **macro["2026-01"]},
        {"Month": "2026-02", "Category_Key": "TRADE", "Row_Basis": "ALL", **base, **macro["2026-02"]},
    ]
    return pd.DataFrame(rows)


def test_build_lookup_uses_the_training_formulas():
    lookup = bmc.build_lookup(_toy_category_month(), created="2026-10-22T00:00:00")

    assert lookup["months"] == ["2026-01", "2026-02"]
    jan = bmc.lookup_values(lookup, "TRADE", "2026-01")
    assert jan["F_Mkt_Pressure_t"] == 4.0 and jan["F_Mkt_Pressure_Change_1M"] == 3.0
    assert jan["F_Mkt_Volatility_Change_1M"] == -1.0 and jan["F_Mkt_Pressure_Tier_Ord_t_minus_1"] == 1.0
    assert jan["F_Mkt_Evidence_Missing"] == 0
    assert jan["F_Macro_CCPI_YoY_Change_1M"] == 0.5
    assert math.isclose(jan["F_Macro_Food_Index_Change_1M_pct"], 10.0)
    assert math.isclose(jan["F_Macro_Diesel_Change_1M_pct"], 20.0)


def test_build_lookup_marks_missing_evidence_like_training():
    lookup = bmc.build_lookup(_toy_category_month())

    no_evidence = bmc.lookup_values(lookup, "TRADE", "2026-02")
    new_category = bmc.lookup_values(lookup, "BEAUTY AND WELLNESS", "2026-01")  # no market rows at all
    for values in (no_evidence, new_category):
        assert values["F_Mkt_Evidence_Missing"] == 1
        assert all(values[f] is None for f in fx.MARKET_FEATURES if f != "F_Mkt_Evidence_Missing")
    assert new_category["F_Macro_CCPI_YoY_t"] == 2.0
    assert bmc.lookup_values(lookup, "TRADE", "2026-03") is None


def test_build_lookup_contains_no_household_fields():
    lookup = bmc.build_lookup(_toy_category_month())

    assert set(lookup) == {"description", "created", "source_note", "built_by", "months", "category_keys",
                           "level_keys", "market_features", "macro_features", "market", "macro"}
    for months in lookup["market"].values():
        for values in months.values():
            assert list(values) == fx.MARKET_FEATURES
    for values in lookup["macro"].values():
        assert list(values) == fx.MACRO_FEATURES


def test_verify_matches_the_training_join():
    table = _toy_category_month()
    panel = pd.DataFrame({"category_key": ["TRADE", "TRADE", "TRANSPORT & LOGISTICS"],
                          "month": ["2026-01", "2026-02", "2026-02"]})
    joined = fx.join_market_macro(panel["month"], panel["category_key"], table)
    features = fx.market_macro_features(joined)

    result = bmc.verify(panel, features, bmc.build_lookup(table))

    assert result["rows_all_13_equal"] == 3 and result["values_equal"] == result["values_checked"] == 39


# ------------------------------------------------------ committed lookup ----
def test_lookup_file_covers_every_key_month_and_feature():
    lookup = market_context.load_lookup()

    assert lookup["months"] == sorted(lookup["months"])
    assert lookup["market_features"] + lookup["macro_features"] == fx.CONTEXT_FEATURES
    assert list(MarketContextFeatures.model_fields) == fx.CONTEXT_FEATURES
    assert set(lookup["market"]) == set(fx.KEY_TO_LEVEL) and set(lookup["macro"]) == set(lookup["months"])
    for months in lookup["market"].values():
        assert set(months) == set(lookup["months"])


def test_lookup_levels_match_the_deployed_models():
    levels = loader.load_metadata("3M")["categorical_levels"]["F_Category"]

    assert set(market_context.load_lookup()["level_keys"]) == set(levels)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Trade", ("Trade", "TRADE")),
        ("  trade ", ("Trade", "TRADE")),
        ("TRANSPORT & LOGISTICS", ("Transport & Logistics", "TRANSPORT & LOGISTICS")),
        ("Other", ("Other", "OTHER")),
        ("FISHERIES & AQUACULTURE", ("Other", "FISHERIES & AQUACULTURE")),
        ("Space Tourism", None),
    ],
)
def test_resolve_category(value, expected):
    assert market_context.resolve_category(value) == expected


# ----------------------------------------------------------------- service ----
def test_service_in_range_returns_the_lookup_values():
    month = market_context.load_lookup()["months"][0]
    result = services.get_market_context("Agriculture & Plantation Crops", month)

    assert result.in_data_range
    assert result.features.model_dump() == market_context.context_values("AGRICULTURE & PLANTATION CROPS", month)
    assert result.evidence_missing == bool(result.features.F_Mkt_Evidence_Missing)


def test_service_month_outside_the_data_is_all_null():
    result = services.get_market_context("Trade", "2030-01")

    assert not result.in_data_range and result.evidence_missing
    assert all(value is None for value in result.features.model_dump().values())
    assert "2030-01" in result.note and "not estimated" in result.note


def test_service_errors():
    with pytest.raises(services.UnknownCategoryError):
        services.get_market_context("Space Tourism", "2026-01")
    with pytest.raises(ValueError):
        services.get_market_context("Trade", "2026-1")


# ---------------------------------------------------------------- endpoint ----
def test_endpoint_returns_13_features_and_months():
    response = client.get(URL, params={"category": "TRADE", "month": "2026-03"})

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "Trade" and body["category_key"] == "TRADE" and body["month"] == "2026-03"
    assert list(body["features"]) == fx.CONTEXT_FEATURES
    assert body["available_months"] == market_context.load_lookup()["months"]
    assert body["source_note"]


def test_endpoint_new_category_has_macro_but_no_market_evidence():
    body = client.get(URL, params={"category": "Beauty & Wellness", "month": "2026-05"}).json()

    assert body["in_data_range"] and body["evidence_missing"]
    assert body["features"]["F_Mkt_Evidence_Missing"] == 1 and body["features"]["F_Mkt_Pressure_t"] is None
    assert body["features"]["F_Macro_CCPI_YoY_t"] is not None
    assert body["note"]


def test_endpoint_month_outside_the_data_is_200_with_nulls():
    response = client.get(URL, params={"category": "Trade", "month": "2025-12"})

    assert response.status_code == 200
    assert response.json()["in_data_range"] is False
    assert all(value is None for value in response.json()["features"].values())


@pytest.mark.parametrize(
    "params",
    [
        {"category": "Space Tourism", "month": "2026-03"},
        {"category": "Trade", "month": "2026-13"},
        {"category": "Trade", "month": "March"},
        {"month": "2026-03"},
        {"category": "Trade"},
    ],
)
def test_endpoint_rejects_bad_input_with_422(params):
    assert client.get(URL, params=params).status_code == 422


def test_market_context_values_feed_predict(metadata):
    from app.components.market_risk.tests.conftest import build_features

    context = client.get(URL, params={"category": "Agriculture & Plantation Crops", "month": "2026-03"}).json()
    features = build_features(metadata, F_Category="Agriculture & Plantation Crops", **context["features"])

    response = client.post("/api/risk/predict", json={"horizon": "both", "features": features})

    assert response.status_code == 200
    assert not any("median-imputed" in w for w in response.json()["warnings"])
