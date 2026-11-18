"""v2 rule, feature and leakage tests on small synthetic rows. No artifacts needed."""

import numpy as np
import pandas as pd
import pytest

from app.components.market_risk.v2 import pipeline

NAN = np.nan


def visit(**values) -> pd.DataFrame:
    row = {"business_running": 1.0, "profit": 1.0, "coach_progressing": 1.0, "market_stress_any": 0.0}
    row.update(values)
    return pd.DataFrame([row])


def risk(**values) -> str:
    return pipeline.classify(visit(**values), 2).iloc[0]


def row_reasons(**values) -> list[str]:
    frame = visit(**values)
    frame["risk_class_t"] = pipeline.classify(frame, 2)
    return pipeline.reasons(frame.iloc[0])


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({}, "Low"),
        ({"profit": 0.0}, "Medium"),
        ({"profit": 0.0, "coach_progressing": 0.0}, "High"),
        ({"coach_progressing": 0.0, "market_stress_any": 1.0}, "High"),
        ({"business_running": 0.0}, "High"),
        ({"business_running": 0.0, "profit": NAN, "coach_progressing": NAN, "market_stress_any": NAN}, "High"),
        ({"profit": NAN}, "Unassigned"),
        ({"profit": 0.0, "market_stress_any": NAN}, "Unassigned"),
        ({"profit": 0.0, "coach_progressing": 0.0, "market_stress_any": NAN}, "High"),
    ],
)
def test_risk_rule(values, expected):
    assert risk(**values) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"business_running": NAN}, "Unassigned"),
        ({"business_running": NAN, "profit": 0.0}, "Unassigned"),
        ({"business_running": NAN, "profit": 0.0, "coach_progressing": 0.0}, "High"),
    ],
)
def test_blank_business_is_unassigned_unless_signals_give_high(values, expected):
    assert risk(**values) == expected


def test_reasons_use_notebook_wording():
    assert row_reasons() == ["no warning signals"]
    assert row_reasons(business_running=0.0) == ["business not running"]
    assert row_reasons(profit=0.0, market_stress_any=1.0) == [
        "no profit last month",
        "market stress (low sales / input cost / inputs unavailable)",
    ]
    assert row_reasons(coach_progressing=NAN) == ["form incomplete: coach unknown - ask SDO"]
    assert row_reasons(business_running=NAN) == ["form incomplete: business status unknown - ask SDO"]


def synthetic_tables() -> pipeline.PipelineTables:
    months = [f"2026-{m:02d}" for m in range(1, 7)]
    market = pd.DataFrame([
        {"district": "Badulla", "category": category, "month": month,
         "market_pressure": 0.6, "market_pressure_level": "Moderate", "price_month_used": month,
         "series": "test series", "ipa_basis": "quarterly only", "dmc_affected_families": 0.0,
         **{column: 1.0 for column in pipeline.AREA}}
        for category in ("TRADE", "OTHER") for month in months
    ])
    return pipeline.PipelineTables(
        opl=pd.DataFrame({"month": ["2026-01", "2026-03"], "national_opl_lkr": [15000.0, 25000.0]}),
        market=market,
        macro=pd.DataFrame({"month": months, "ccpi_anomaly": 0.1, "diesel_anomaly": 0.2}),
        revenue_upper={0: 10000.0, 1: 20000.0, 2: 30000.0, 3: NAN},
        k_high=2,
    )


def synthetic_visits(months: list[int], key: str = "SIM-HH-TEST") -> pd.DataFrame:
    rows = []
    for month in months:
        rows.append({
            "household_key": key, "is_synthetic": True, "monitoring_period": f"2026-{month:02d}",
            "district": "Badulla", "category": "TRADE", "business_running": 1,
            "profit": month % 2, "coach_progressing": 1, "revenue_band": month % 3,
            "problem_sales_low": 1 if month % 3 == 0 else 0, "problem_input_cost": 0,
            "problem_input_unavailable": 0,
        })
    return pd.DataFrame(rows)


def test_revenue_low_uses_latest_poverty_line_on_or_before_month():
    visits = synthetic_visits([1, 2, 3])
    visits["revenue_band"] = [1, 1, 1]
    features = pipeline.build_features(visits, synthetic_tables())
    assert features.opl_month_used.tolist() == ["2026-01", "2026-01", "2026-03"]
    assert features.revenue_low.tolist() == [0.0, 0.0, 1.0]


def test_open_ended_band_is_not_low_and_blank_band_is_null():
    visits = synthetic_visits([3, 4])
    visits["revenue_band"] = [3, NAN]
    features = pipeline.build_features(visits, synthetic_tables())
    assert features.revenue_low.iloc[0] == 0.0
    assert pd.isna(features.revenue_low.iloc[1])


def test_history_does_not_change_when_later_months_are_added():
    tables = synthetic_tables()
    full = pipeline.build_features(synthetic_visits([1, 2, 3, 4, 5, 6]), tables)
    for last in range(1, 6):
        truncated = pipeline.build_features(synthetic_visits(list(range(1, last + 1))), tables)
        pd.testing.assert_frame_equal(
            truncated[pipeline.HCOLS].reset_index(drop=True),
            full[pipeline.HCOLS].iloc[:last].reset_index(drop=True),
        )


def test_first_visit_differs_from_visit_without_household_key():
    tables = synthetic_tables()
    first = pipeline.build_features(synthetic_visits([1]), tables).iloc[0]
    assert first.n_prior_visits == 0
    assert first.tenure_months == 0
    keyless = synthetic_visits([1])
    keyless["household_key"] = None
    row = pipeline.build_features(keyless, tables).iloc[0]
    assert row[pipeline.HCOLS].isna().all()


def test_unassigned_category_uses_other_market_row():
    visits = synthetic_visits([2])
    visits["category"] = "UNASSIGNED"
    row = pipeline.build_features(visits, synthetic_tables()).iloc[0]
    assert row.market_pressure == 0.6
    assert row.market_pressure_level == "Moderate"


def test_shap_values_are_summed_over_feature_and_missing_indicator():
    names = ["profit", "missingindicator_profit", "hours_band", "category_TRADE", "category_OTHER"]
    totals = pipeline.group_contributions(names, np.array([0.1, 0.2, -0.3, 0.05, 0.05]))
    assert totals["profit"] == pytest.approx(0.3)
    assert totals["hours_band"] == pytest.approx(-0.3)
    assert totals["category"] == pytest.approx(0.1)


def test_every_core_feature_has_a_label_and_group():
    core = pipeline.A + pipeline.P + ["problem_count", "market_stress_any"] + pipeline.HCOLS + pipeline.D + pipeline.CUR
    assert not [name for name in core if name not in pipeline.FEATURE_LABELS]
    assert {pipeline.FEATURE_GROUPS[name] for name in core} == {
        "Business", "Household shock", "History", "Market", "Current risk",
    }
