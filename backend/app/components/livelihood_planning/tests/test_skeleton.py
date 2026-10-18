"""Tests for the livelihood-planning modules."""

import importlib

import pytest

from app.components.livelihood_planning import services
from app.components.livelihood_planning.data_prep import (
    extract_plans,
    load_to_supabase,
)
from app.components.livelihood_planning.model_1_recommend.predict import (
    recommend_top_k,
)
from app.components.livelihood_planning.model_2_swot.factors import (
    get_livelihood_factors,
)
from app.components.livelihood_planning.model_2_swot.scoring import score_factors
from app.components.livelihood_planning.model_2_swot.swot import build_swot
from app.components.livelihood_planning.model_3_plan.checker import check_plan
from app.components.livelihood_planning.model_3_plan.finance import build_financials
from app.components.livelihood_planning.model_3_plan.retrieval import (
    retrieve_chunks,
)
from app.components.livelihood_planning.model_3_plan.writer import write_plan
from app.components.livelihood_planning.schemas import (
    OFFICIAL_LIVELIHOOD_CATEGORIES,
)

NEW_MODULES = (
    "app.components.livelihood_planning.model_1_recommend",
    "app.components.livelihood_planning.model_1_recommend.loader",
    "app.components.livelihood_planning.model_1_recommend.predict",
    "app.components.livelihood_planning.model_2_swot",
    "app.components.livelihood_planning.model_2_swot.factors",
    "app.components.livelihood_planning.model_2_swot.scoring",
    "app.components.livelihood_planning.model_2_swot.swot",
    "app.components.livelihood_planning.model_3_plan",
    "app.components.livelihood_planning.model_3_plan.retrieval",
    "app.components.livelihood_planning.model_3_plan.writer",
    "app.components.livelihood_planning.model_3_plan.finance",
    "app.components.livelihood_planning.model_3_plan.checker",
    "app.components.livelihood_planning.data_prep.extract_plans",
    "app.components.livelihood_planning.data_prep.load_to_supabase",
)


def test_all_new_python_modules_import():
    for module_name in NEW_MODULES:
        assert importlib.import_module(module_name)


def test_main_app_imports_without_project_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main_module = importlib.import_module("app.main")

    assert main_module.app


def test_model_recommendations_have_the_expected_shape():
    recommendations = recommend_top_k({}, k=3)

    assert len(OFFICIAL_LIVELIHOOD_CATEGORIES) == 9
    assert len(recommendations) == 3
    assert all(
        {"livelihood", "score"}.issubset(item) for item in recommendations
    )
    assert all(isinstance(item["score"], float) for item in recommendations)
    assert all(0.0 <= item["score"] <= 1.0 for item in recommendations)
    assert [item["score"] for item in recommendations] == sorted(
        (item["score"] for item in recommendations), reverse=True
    )


def test_swot_placeholders_have_the_expected_shape():
    factors = get_livelihood_factors("TRADE")
    scored_factors = score_factors(factors, {})
    result = build_swot("TRADE", {})

    assert factors
    assert all("score" in factor for factor in scored_factors)
    assert set(result) == {
        "strengths",
        "weaknesses",
        "opportunities",
        "threats",
    }
    assert all(
        set(item) == {"text", "source"}
        for items in result.values()
        for item in items
    )


def test_plan_placeholders_have_the_expected_shape():
    swot = build_swot("TRADE", {})
    financials = build_financials("TRADE", {})
    context = retrieve_chunks("trade plan")
    plan = write_plan("TRADE", swot, financials, context)
    result = check_plan(plan)

    assert financials["placeholder"] is True
    assert context == []
    assert plan["placeholder"] is True
    assert result == {"ok": True, "issues": []}


def test_public_service_returns_the_full_placeholder_chain():
    result = services.recommend_livelihood({})

    assert {
        "recommendations",
        "swot",
        "plan",
        "placeholder",
        "confidence",
        "notes",
    }.issubset(result)
    assert result["recommendations"]
    assert result["plan"]["validation"] == {"ok": True, "issues": []}
    assert result["placeholder"] is True


def test_manual_data_prep_functions_are_not_implemented():
    with pytest.raises(NotImplementedError, match="Plan extraction"):
        extract_plans.extract_plan("scan.pdf", "plan.json")

    with pytest.raises(NotImplementedError, match="Supabase loading"):
        load_to_supabase.load_cleaned_records([], "plans")
