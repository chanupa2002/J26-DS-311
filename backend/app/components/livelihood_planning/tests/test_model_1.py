"""Focused tests for the real Model 1 artifact and inference path."""

import joblib
import numpy as np
import pytest
import sklearn

from app.components.livelihood_planning.model_1_recommend import loader, predict
from app.components.livelihood_planning.model_1_recommend.predict import (
    recommend_top_k,
    recommend_with_context,
)

CLOSE_SCORE_NOTE = "The top suggestions are close in score; review them carefully."
COVERAGE_NOTE = (
    "Low confidence for {district}. Results are general suggestions; "
    "review carefully."
)


@pytest.fixture(autouse=True)
def clear_model_cache():
    loader.load_model.cache_clear()
    yield
    loader.load_model.cache_clear()


def set_model_probabilities(monkeypatch, top_score, second_score):
    model, _, _ = loader.load_model()
    class_count = len(model.classes_)
    other_score = (1.0 - top_score - second_score) / (class_count - 2)
    probabilities = np.full(class_count, other_score)
    probabilities[0] = top_score
    probabilities[1] = second_score
    monkeypatch.setattr(
        model, "predict_proba", lambda frame: np.asarray([probabilities])
    )


def test_returns_three_probabilities_in_descending_order():
    recommendations = recommend_top_k(
        {
            "district": " Colombo ",
            "ds_division": "Colombo",
            "age": 42,
            "gender": "female",
            "female_headed": "TRUE",
            "disability": "no",
            "aswesuma_category": "Poor",
        }
    )

    assert len(recommendations) == 3
    scores = [item["score"] for item in recommendations]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= score <= 1.0 for score in scores)


def test_trained_district_with_close_scores_keeps_normal_confidence(monkeypatch):
    set_model_probabilities(monkeypatch, 0.40, 0.38)

    result = predict.recommend_with_context({"district": "badulla"})

    assert result["confidence"] == "normal"
    assert result["notes"].count(CLOSE_SCORE_NOTE) == 1


def test_untrained_district_has_low_coverage_confidence(monkeypatch):
    set_model_probabilities(monkeypatch, 0.80, 0.10)

    result = recommend_with_context({"district": "Unknown District"})

    assert len(result["recommendations"]) == 3
    assert result["confidence"] == "low"
    assert COVERAGE_NOTE.format(district="Unknown District") in result["notes"]


def test_missing_district_uses_generic_coverage_note(monkeypatch):
    set_model_probabilities(monkeypatch, 0.80, 0.10)

    result = recommend_with_context({})

    assert result["confidence"] == "low"
    assert COVERAGE_NOTE.format(district="this district") in result["notes"]


def test_trained_district_with_clear_leader_has_no_close_note(monkeypatch):
    set_model_probabilities(monkeypatch, 0.80, 0.10)

    result = recommend_with_context({"district": "Badulla"})

    assert result["confidence"] == "normal"
    assert CLOSE_SCORE_NOTE not in result["notes"]


def test_missing_optional_fields_do_not_crash():
    recommendations = recommend_top_k({})

    assert len(recommendations) == 3


def test_reasons_are_short_string_lists_without_unknown():
    recommendations = recommend_top_k(
        {
            "district": "Badulla",
            "ds_division": "Mahiyanganaya",
            "age": 36,
            "gender": "Female",
            "female_headed": True,
            "disability": False,
            "aswesuma_category": "Poor",
        }
    )

    for recommendation in recommendations:
        assert isinstance(recommendation["reasons"], list)
        assert len(recommendation["reasons"]) <= 3
        assert all(isinstance(reason, str) for reason in recommendation["reasons"])
        assert all("Unknown" not in reason for reason in recommendation["reasons"])


def test_model_artifacts_are_loaded_only_once(monkeypatch):
    real_joblib_load = joblib.load
    load_count = 0

    def counting_load(*args, **kwargs):
        nonlocal load_count
        load_count += 1
        return real_joblib_load(*args, **kwargs)

    monkeypatch.setattr(joblib, "load", counting_load)

    first = loader.load_model()
    second = loader.load_model()

    assert first is second
    assert load_count == 1
    assert loader.load_model.cache_info().hits == 1


def test_sklearn_version_mismatch_raises_runtime_error(monkeypatch):
    monkeypatch.setattr(sklearn, "__version__", "0.0-test")

    with pytest.raises(RuntimeError, match="Install the pinned version or retrain"):
        loader.load_model()
