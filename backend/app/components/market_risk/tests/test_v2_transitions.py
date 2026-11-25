"""Monthly transition summary ("1M"): estimated from stored simulated visits, never typed.

Unit tests use small synthetic frames; endpoint tests use the synthetic store only.
"""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.components.market_risk.v2 import artifacts, transitions
from app.components.market_risk.v2.schemas import EXAMPLE_VISIT
from app.main import app

BASE = "/api/risk/v2"
client = TestClient(app)
CLASSES = ["Low", "Medium", "High"]
ANSWERS = ("business_running", "profit", "coach_progressing", "revenue_band", "hours_band",
           "record_keeping", "borrowed_money", "saved_money", "grant_status", "problem_sales_low",
           "problem_input_cost", "problem_input_unavailable")


@pytest.fixture
def needs_artifacts():
    if artifacts.missing_files():
        pytest.skip("v2 artifacts are not on this machine (they are git-ignored)")


def frame(rows):
    return pd.DataFrame(rows, columns=["household_key", "month_index", "risk_class_t"])


# --- unit tests on small synthetic frames -------------------------------------------------

def test_only_one_month_steps_with_known_classes_are_counted():
    visits = frame([
        ("SIM-HH-A", 1, "Low"), ("SIM-HH-A", 2, "Medium"),       # counted: Low -> Medium
        ("SIM-HH-A", 4, "High"),                                  # gap of 2 months: skipped
        ("SIM-HH-A", 5, "Unassigned"),                            # unknown class: skipped both ways
        ("SIM-HH-A", 6, "High"),
        ("SIM-HH-B", 3, "High"), ("SIM-HH-B", 2, "High"),        # unsorted input: High -> High
        ("SIM-HH-C", 7, "Low"),                                   # other household, no pair
    ])
    pairs = transitions.pairs(visits)
    assert sorted(map(tuple, pairs.values.tolist())) == [("High", "High"), ("Low", "Medium")]


def test_households_are_not_mixed():
    visits = frame([("SIM-HH-A", 1, "Low"), ("SIM-HH-B", 2, "High")])
    assert transitions.estimate(visits).n_transitions == 0


def test_laplace_smoothing_and_rows_sum_to_one():
    result = transitions.estimate(frame([("SIM-HH-A", 1, "Low"), ("SIM-HH-A", 2, "Low")]))
    assert result.n_transitions == 1
    assert result.counts.tolist() == [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    np.testing.assert_allclose(result.matrix[0], [2 / 4, 1 / 4, 1 / 4])
    np.testing.assert_allclose(result.matrix[1], [1 / 3] * 3)
    np.testing.assert_allclose(result.matrix.sum(axis=1), 1)


def test_unassigned_gives_null_chances():
    result = transitions.estimate(frame([("SIM-HH-A", 1, "Low"), ("SIM-HH-A", 2, "High")]))
    entry = result.next_month("Unassigned")
    assert entry["p_low"] is entry["p_medium"] is entry["p_high"] is entry["predicted_class"] is None
    assert entry["note"] == transitions.UNKNOWN_NOTE
    assert entry["alert"] is None
    assert result.row_summary("Unassigned") == {"next_month_class": None, "next_month_p_high": None}


# --- the estimate from the stored simulated visits -----------------------------------------

def recount(features: pd.DataFrame) -> np.ndarray:
    """Independent recount with a plain loop, to check transitions.estimate."""
    counts = np.zeros((3, 3), dtype=int)
    for _, visits in features.groupby("household_key"):
        ordered = visits.sort_values("month_index")
        steps = zip(ordered.month_index, ordered.risk_class_t)
        previous = next(steps, None)
        for current in steps:
            if current[0] - previous[0] == 1 and previous[1] in CLASSES and current[1] in CLASSES:
                counts[CLASSES.index(previous[1]), CLASSES.index(current[1])] += 1
            previous = current
    return counts


def test_store_estimate_matches_recount_and_is_smoothed(needs_artifacts):
    bundle = artifacts.load_bundle()
    estimate = bundle.transitions
    assert bundle.store_features.household_key.str.startswith("SIM-HH-").all()
    counts = recount(bundle.store_features)
    assert estimate.counts.astype(int).tolist() == counts.tolist()
    assert estimate.n_transitions == counts.sum() > 0
    np.testing.assert_allclose(estimate.matrix, (counts + 1) / (counts + 1).sum(axis=1, keepdims=True))
    np.testing.assert_allclose(estimate.matrix.sum(axis=1), 1)


# --- endpoints -----------------------------------------------------------------------------

def test_visit_has_1m_from_the_matrix(needs_artifacts):
    body = client.post(f"{BASE}/risk/visit", json=EXAMPLE_VISIT).json()
    entry = body["predictions"]["1M"]
    matrix = artifacts.load_bundle().transitions.matrix
    row = matrix[CLASSES.index(body["current_risk"]["risk_class"])]
    assert [entry["p_low"], entry["p_medium"], entry["p_high"]] == pytest.approx(row.tolist())
    assert entry["predicted_class"] == CLASSES[int(row.argmax())]
    assert entry["method"] == "past monthly transitions"
    assert entry["alert"] is None
    assert entry["n_transitions"] == artifacts.load_bundle().transitions.n_transitions
    assert "Not a machine-learning prediction" in entry["note"]
    assert body["predictions"]["3M"]["alert"] in (True, False)


def test_unassigned_visit_has_null_1m(needs_artifacts):
    blank = {**EXAMPLE_VISIT, **{name: None for name in ANSWERS}}
    body = client.post(f"{BASE}/risk/visit", json=blank).json()
    assert body["current_risk"]["risk_class"] == "Unassigned"
    entry = body["predictions"]["1M"]
    assert entry["p_high"] is None and entry["predicted_class"] is None
    assert entry["note"] == "Current risk unknown – complete the visit form."


def test_household_list_and_timeline_have_next_month(needs_artifacts):
    matrix = artifacts.load_bundle().transitions.matrix
    rows = client.get(f"{BASE}/risk/households").json()["households"]
    timeline = client.get(f"{BASE}/risk/household/SIM-HH-001").json()["timeline"]
    for item in [*rows, *timeline]:
        if item["current_risk"] not in CLASSES:
            assert item["next_month_p_high"] is None and item["next_month_class"] is None
            continue
        row = matrix[CLASSES.index(item["current_risk"])]
        assert item["next_month_p_high"] == pytest.approx(row[2])
        assert item["next_month_class"] == CLASSES[int(row.argmax())]


def test_evidence_has_transition_summary(needs_artifacts):
    summary = client.get(f"{BASE}/model/evidence").json()["transitions"]
    estimate = artifacts.load_bundle().transitions
    assert summary["is_synthetic"] is True
    assert summary["classes"] == CLASSES
    assert summary["counts"] == estimate.counts.astype(int).tolist()
    assert summary["n_transitions"] == sum(map(sum, summary["counts"]))
    assert all(sum(row) == pytest.approx(1) for row in summary["matrix"])
    after = summary["p_high_after"]
    assert [step["months"] for step in after] == [1, 2, 3, 4, 5, 6]
    for step in after:
        power = np.linalg.matrix_power(np.array(summary["matrix"]), step["months"])
        assert [step[name] for name in CLASSES] == pytest.approx(power[:, 2].tolist())
    assert "no 1-month model was trained" in summary["text"]
    assert "SIM-HH-" not in str(summary)
