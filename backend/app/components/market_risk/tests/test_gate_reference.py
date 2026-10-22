"""The retraining reproduction gate is pinned to version 1.0 (ml/training/gate_reference_v1.json).

ml/models/ holds version 2.0 since the 2026-10-21 promotion, so a gate that compared
with ml/models/ would always fail. These tests need no data files.
"""

import copy
import json

import numpy as np
import pandas as pd
import pytest

from app.components.market_risk.ml import loader
from app.components.market_risk.ml.training import features as fx
from app.components.market_risk.ml.training import train_from_cleaned as tfc
from app.components.market_risk.tests.conftest import build_features

V1 = {
    "3M": {"train_n": 102, "test_n": 39, "Macro_F1": 0.3026, "High_Recall": 0.56, "rf": 0.356, "persistence": 0.295},
    "6M": {"train_n": 77, "test_n": 39, "Macro_F1": 0.4302, "High_Recall": 0.88, "rf": 0.431, "persistence": 0.179},
}


@pytest.fixture(scope="module")
def reference():
    return tfc.load_gate_reference()["horizons"]


@pytest.mark.parametrize("horizon", ["3M", "6M"])
def test_reference_holds_the_version_1_numbers(reference, horizon):
    ref, v1 = reference[horizon], V1[horizon]

    assert (ref["train_n"], ref["test_n"]) == (v1["train_n"], v1["test_n"])
    assert ref["test_metrics"] == {"Macro_F1": v1["Macro_F1"], "High_Recall": v1["High_Recall"]}
    assert ref["walk_forward_448"] == {"rf": v1["rf"], "persistence": v1["persistence"]}
    assert ref["walk_forward_448"] == tfc.NOTEBOOK_WALK_FORWARD_448[horizon]
    assert ref["best_params"] == {"max_depth": 3, "min_samples_leaf": 10}
    assert ref["created"] == "2026-10-20T04:23:25" and "58 households" in ref["data_basis"]


@pytest.mark.parametrize("horizon", ["3M", "6M"])
def test_reference_is_not_the_deployed_version_2(reference, horizon):
    deployed = loader.load_metadata(horizon)

    assert tfc.load_gate_reference()["model_version"] == "1.0"
    assert tfc.GATE_REFERENCE_PATH.parent != tfc.CURRENT_MODELS_DIR
    assert reference[horizon]["created"] != deployed["created"]
    assert reference[horizon]["train_n"] != deployed["train_n"]


@pytest.mark.parametrize("horizon", ["3M", "6M"])
def test_reference_statistics_fit_the_feature_lists(reference, horizon):
    stats = reference[horizon]["training_statistics"]
    n_indicators = len(stats["missing_indicator_features"])

    assert len(stats["imputer_medians"]) == len(fx.FEATURES_NUM)
    assert len(stats["scaler_mean"]) == len(stats["scaler_scale"]) == len(fx.FEATURES_NUM) + n_indicators
    assert len(stats["onehot_categories"]) == len(fx.FEATURES_CAT)


def _passing_inputs(ref):
    return dict(train_n=ref["train_n"], test_n=ref["test_n"], test_metrics=dict(ref["test_metrics"]),
                statistics=copy.deepcopy(ref["training_statistics"]),
                wf_rf=ref["walk_forward_448"]["rf"], wf_persistence=ref["walk_forward_448"]["persistence"])


@pytest.mark.parametrize("horizon", ["3M", "6M"])
def test_gate_passes_on_the_version_1_values(reference, horizon):
    assert tfc.gate_check(reference[horizon], **_passing_inputs(reference[horizon]))["passed"]


@pytest.mark.parametrize("horizon", ["3M", "6M"])
def test_gate_fails_against_the_deployed_version_2_metadata(reference, horizon):
    """The old bug: expected values taken from ml/models/ (v2.0) can never match a 448-row refit."""
    deployed = loader.load_metadata(horizon)
    v2_as_reference = {**reference[horizon], "train_n": deployed["train_n"], "test_n": deployed["test_n"],
                       "test_metrics": deployed["test_metrics"]}

    assert not tfc.gate_check(v2_as_reference, **_passing_inputs(reference[horizon]))["passed"]


@pytest.mark.parametrize(
    "change, failed_check",
    [
        (lambda i: i.update(train_n=i["train_n"] + 1), "sizes"),
        (lambda i: i["test_metrics"].update(Macro_F1=i["test_metrics"]["Macro_F1"] + 1e-3), "macro_f1"),
        (lambda i: i["test_metrics"].update(High_Recall=i["test_metrics"]["High_Recall"] - 1e-3), "high_recall"),
        (lambda i: i.update(wf_rf=i["wf_rf"] + 1e-3), "walk_forward"),
        (lambda i: i["statistics"]["scaler_mean"].__setitem__(0, i["statistics"]["scaler_mean"][0] + 1e-6), "statistics"),
        (lambda i: i["statistics"]["onehot_categories"][0].append("New level"), "statistics"),
    ],
)
def test_each_gate_check_can_fail(reference, change, failed_check):
    inputs = _passing_inputs(reference["3M"])
    change(inputs)

    result = tfc.gate_check(reference["3M"], **inputs)

    assert not result[failed_check] and not result["passed"]


def test_pipeline_statistics_round_trip_through_json():
    meta = loader.load_metadata("3M")
    levels = meta["categorical_levels"]["F_Category"]
    rows = [build_features(meta, F_Age=20.0 + i, F_Category=levels[i % 3], F_Mkt_Pressure_t=None if i % 2 else 1.5 * i)
            for i in range(12)]
    X = pd.DataFrame(rows)[fx.FEATURES]
    model = tfc.rf_pipeline(max_depth=2, min_samples_leaf=1).fit(X, np.arange(12) % 3)

    stats = tfc.pipeline_statistics(model)
    reloaded = json.loads(json.dumps(stats))

    assert tfc.same_statistics(stats, reloaded)
    shorter = {**reloaded, "imputer_medians": reloaded["imputer_medians"][:-1]}
    assert not tfc.same_statistics(stats, shorter)
