"""Parity of the v2 pipeline with the notebook, on all 877 visits.

NDA: the data files contain real visits. Every assertion and message here carries
counts and column names only. Row values are never printed.
"""

import numpy as np
import pandas as pd
import pytest

from app.components.market_risk.v2 import artifacts, pipeline

FIXTURE = "parity_fixture_ALL.csv"
FEATURE_TOLERANCE = 1e-6
PROBABILITY_TOLERANCE = 1e-3

NUMERIC_COLUMNS = [
    *pipeline.A, *pipeline.P, "problem_count", "market_stress_any", *pipeline.HCOLS, *pipeline.D,
    *pipeline.AREA, *pipeline.F, *pipeline.CUR, "opl_lkr",
]
TEXT_COLUMNS = ["risk_class_t", "opl_month_used", "market_pressure_level", "market_price_month_used",
                "market_series", "market_ipa_basis"]


@pytest.fixture(scope="module")
def parity():
    missing = artifacts.missing_files()
    folder = artifacts.artifacts_dir()
    if missing or not (folder / FIXTURE).is_file():
        pytest.skip("v2 artifacts are not on this machine (they are git-ignored); parity test skipped")
    bundle = artifacts.load_bundle()
    visits = pd.read_csv(
        folder / artifacts.VISITS_FILE, usecols=pipeline.VISIT_INPUT_COLUMNS,
        dtype={"household_key": "string"}, low_memory=False,
    )
    expected = pd.read_csv(folder / FIXTURE, dtype={"household_key": "string"}, low_memory=False)
    features = pipeline.build_features(visits, bundle.tables)
    predictions = pipeline.predict_visits(features, bundle.models, bundle.meta)
    return features, predictions, expected, expected.is_synthetic.astype(bool).to_numpy()


def counts(matches: np.ndarray, synthetic: np.ndarray) -> str:
    return (
        f"synthetic {int(matches[synthetic].sum())}/{int(synthetic.sum())}, "
        f"real {int(matches[~synthetic].sum())}/{int((~synthetic).sum())}"
    )


def numeric_matches(actual: pd.Series, expected: pd.Series, tolerance: float) -> np.ndarray:
    a = pd.to_numeric(actual, errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(expected, errors="coerce").to_numpy(dtype=float)
    with np.errstate(invalid="ignore"):
        return (np.isnan(a) & np.isnan(b)) | (np.abs(a - b) <= tolerance)


def text_matches(actual: pd.Series, expected: pd.Series) -> np.ndarray:
    return actual.astype("object").where(actual.notna(), "").astype(str).to_numpy() == (
        expected.astype("object").where(expected.notna(), "").astype(str).to_numpy()
    )


def report(name: str, matches: np.ndarray, synthetic: np.ndarray) -> int:
    print(f"parity {name}: {counts(matches, synthetic)}")
    return int((~matches).sum())


def test_fixture_covers_all_visits(parity):
    features, _, expected, synthetic = parity
    assert len(features) == len(expected) == 877
    assert int(synthetic.sum()) == 778
    assert int((~synthetic).sum()) == 99


def test_numeric_features_match_notebook(parity):
    features, _, expected, synthetic = parity
    failed = []
    all_match = np.ones(len(expected), dtype=bool)
    for column in NUMERIC_COLUMNS:
        matches = numeric_matches(features[column], expected[column], FEATURE_TOLERANCE)
        all_match &= matches
        if not matches.all():
            failed.append(f"{column} ({counts(matches, synthetic)})")
    report(f"{len(NUMERIC_COLUMNS)} numeric features, all equal", all_match, synthetic)
    assert not failed, "; ".join(failed)


def test_text_features_match_notebook(parity):
    features, _, expected, synthetic = parity
    failed = []
    for column in TEXT_COLUMNS:
        matches = text_matches(features[column], expected[column])
        report(column, matches, synthetic)
        if not matches.all():
            failed.append(f"{column} ({counts(matches, synthetic)})")
    assert not failed, "; ".join(failed)


def test_current_risk_reasons_match_notebook(parity):
    features, _, expected, synthetic = parity
    actual = pd.Series(["; ".join(pipeline.reasons(row)) for _, row in features.iterrows()])
    matches = text_matches(actual, expected.current_risk_reasons)
    mismatches = report("current_risk_reasons", matches, synthetic)
    assert mismatches == 0, f"reasons differ: {counts(matches, synthetic)}"


@pytest.mark.parametrize("horizon", pipeline.HORIZONS)
def test_probabilities_and_classes_match_notebook(parity, horizon):
    _, predictions, expected, synthetic = parity
    probability = numeric_matches(
        predictions[f"P_High_{horizon}"], expected[f"P_High_{horizon}"], PROBABILITY_TOLERANCE
    )
    predicted = text_matches(predictions[f"predicted_{horizon}"], expected[f"predicted_{horizon}"])
    bad_probability = report(f"P_High_{horizon}", probability, synthetic)
    bad_class = report(f"predicted_{horizon}", predicted, synthetic)
    assert bad_probability == 0, f"P(High) differs: {counts(probability, synthetic)}"
    assert bad_class == 0, f"class differs: {counts(predicted, synthetic)}"


def test_3m_alert_matches_notebook_and_6m_has_none(parity):
    _, predictions, expected, synthetic = parity
    actual = predictions.high_alert_3M.astype(bool).to_numpy()
    notebook = expected.high_alert_3M.astype(str).str.lower().eq("true").to_numpy()
    matches = actual == notebook
    mismatches = report("high_alert_3M", matches, synthetic)
    assert mismatches == 0, f"alert differs: {counts(matches, synthetic)}"
    assert int(predictions.high_alert_6M.notna().sum()) == 0


def test_history_does_not_change_when_later_months_are_added():
    if artifacts.missing_files():
        pytest.skip("v2 artifacts are not on this machine (they are git-ignored)")
    bundle = artifacts.load_bundle()
    visits, full = bundle.store_visits, bundle.store_features
    differences = checked = 0
    for month in sorted(visits.monitoring_period.unique()):
        kept = visits[visits.monitoring_period <= month]
        partial = pipeline.build_features(kept, bundle.tables)
        rows = partial.index[partial.monitoring_period == month]
        for column in pipeline.HCOLS:
            matches = numeric_matches(partial.loc[rows, column], full.loc[rows, column], 0.0)
            checked += len(matches)
            differences += int((~matches).sum())
    print(f"leakage: {checked} values checked, {differences} differences")
    assert checked > 0
    assert differences == 0, f"{differences} history values changed"


def test_store_holds_synthetic_households_only():
    if artifacts.missing_files():
        pytest.skip("v2 artifacts are not on this machine (they are git-ignored)")
    store = artifacts.load_bundle().store_visits
    assert bool(store.is_synthetic.astype(bool).all())
    assert bool(store.household_key.str.startswith("SIM-HH-").all())
