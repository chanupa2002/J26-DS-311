"""Tests for grounded SWOT retrieval, scoring, writing, and viability."""

from types import SimpleNamespace

import pytest

from app.components.livelihood_planning.model_2_swot import (
    factors,
    scoring,
    swot,
    writer,
)
from app.components.livelihood_planning.model_2_swot.grounding import (
    grounded_or_original,
    numbers_are_grounded,
)

SWOT_KEYS = {"strengths", "weaknesses", "opportunities", "threats"}


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def or_(self, *args, **kwargs):
        return self

    def is_(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class FakeSupabase:
    def __init__(self, tables=None, rpc_rows=None):
        self.tables = tables or {}
        self.rpc_rows = rpc_rows or []
        self.rpc_name = None
        self.rpc_params = None

    def table(self, name):
        return FakeQuery(self.tables.get(name, []))

    def rpc(self, name, params):
        self.rpc_name = name
        self.rpc_params = params
        return FakeQuery(self.rpc_rows)


def test_grounding_accepts_rounding_and_rejects_new_numbers():
    source = "Observed viability was 57.4 out of 100."

    assert numbers_are_grounded("Viability was 57 out of 100.", source)
    assert not numbers_are_grounded("Viability was 58 out of 100.", source)
    assert grounded_or_original("Viability was 58 out of 100.", source) == source


def test_embedding_vector_is_l2_normalized():
    assert factors._l2_normalize([3.0, 4.0]) == pytest.approx([0.6, 0.8])


def test_factor_retrieval_maps_swot_and_adds_similarity(monkeypatch):
    client = FakeSupabase(
        tables={
            "livelihood_facts": [
                {
                    "fact_id": 1,
                    "livelihood": "TRADE",
                    "district": "Badulla",
                    "statement": "Trade has observed local demand.",
                    "value": 61,
                    "is_estimated": False,
                    "source": "Survey",
                    "n_obs": 20,
                    "swot": "Strength",
                },
                {
                    "fact_id": 2,
                    "livelihood": "ALL",
                    "district": None,
                    "statement": "Flood exposure can disrupt transport.",
                    "value": None,
                    "is_estimated": True,
                    "source": "Risk index",
                    "n_obs": None,
                    "swot": "Threat",
                },
            ]
        },
        rpc_rows=[{"fact_id": 1, "similarity": 0.82}],
    )
    monkeypatch.setattr(factors, "get_supabase", lambda: client)
    monkeypatch.setattr(factors, "_embed_query", lambda query: [1.0] * 768)

    result = factors.get_livelihood_factors("TRADE", "Badulla")

    assert [item["category"] for item in result] == ["strengths", "threats"]
    assert result[0]["similarity"] == 0.82
    assert {"category", "text", "source", "fact_id", "value", "is_estimated", "n_obs"}.issubset(result[0])
    assert client.rpc_name == "match_livelihood_facts"
    assert client.rpc_params["match_count"] == 10


def test_scoring_keeps_only_top_three_per_category():
    source_factors = [
        {
            "category": "strengths",
            "text": f"Fact {index}",
            "source": "Test",
            "similarity": index / 10,
            "district": "Badulla" if index == 4 else None,
            "is_estimated": index == 0,
        }
        for index in range(5)
    ]

    result = scoring.score_factors(source_factors, {"district": "Badulla"})

    assert len(result) == 3
    assert [item["text"] for item in result] == ["Fact 4", "Fact 3", "Fact 2"]


def test_missing_district_viability_uses_estimated_mean(monkeypatch):
    client = FakeSupabase(
        tables={
            "livelihood_scores": [
                {
                    "district": "Badulla",
                    "viability": 60,
                    "viability_low": 55,
                    "viability_high": 65,
                    "profitability": 50,
                    "market": 60,
                    "area": 70,
                    "resilience": 80,
                    "confidence": "0.8",
                },
                {
                    "district": "Monaragala",
                    "viability": 80,
                    "viability_low": 75,
                    "viability_high": 85,
                    "profitability": 70,
                    "market": 80,
                    "area": 90,
                    "resilience": 100,
                    "confidence": "0.6",
                },
            ]
        }
    )
    monkeypatch.setattr(scoring, "get_supabase", lambda: client)

    result = scoring.get_viability("TRADE", None)

    assert result["score"] == 70
    assert result["confidence"] == pytest.approx(0.7)
    assert result["estimated"] is True


def test_estimated_viability_makes_report_low_confidence(monkeypatch):
    monkeypatch.setattr(
        swot,
        "get_viability",
        lambda livelihood, district: {
            "score": 70.0,
            "low": 65.0,
            "high": 75.0,
            "profitability": 60.0,
            "market": 65.0,
            "area": 80.0,
            "resilience": 75.0,
            "confidence": 0.8,
            "estimated": True,
        },
    )
    monkeypatch.setattr(
        swot,
        "build_swot",
        lambda livelihood, features: {key: [] for key in SWOT_KEYS},
    )

    result = swot.build_swot_report("TRADE", {"district": "Unknown"})

    assert result["confidence"] == "low"
    assert result["viability"]["estimated"] is True
    assert any("estimated" in note.lower() for note in result["notes"])


def test_low_stored_viability_confidence_only_adds_note(monkeypatch):
    monkeypatch.setattr(
        swot,
        "get_viability",
        lambda livelihood, district: {
            "score": 70.0,
            "low": 65.0,
            "high": 75.0,
            "profitability": 60.0,
            "market": 65.0,
            "area": 80.0,
            "resilience": 75.0,
            "confidence": 0.4,
            "estimated": False,
        },
    )
    monkeypatch.setattr(
        swot,
        "build_swot",
        lambda livelihood, features: {key: [] for key in SWOT_KEYS},
    )

    result = swot.build_swot_report("TRADE", {"district": "Badulla"})

    assert result["confidence"] == "normal"
    assert "Stored viability confidence is below 0.5." in result["notes"]


def test_gemini_failure_falls_back_to_source_statement(monkeypatch):
    source = "Observed market score was 61."
    monkeypatch.setattr(
        writer,
        "_generate_rewrites",
        lambda statements: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    result = writer.rewrite_factors([{"text": source, "source": "Survey"}])

    assert result[0]["text"] == source


def test_rewritten_factor_keeps_original_evidence_and_signal_strength(
    monkeypatch,
):
    source = (
        "Demand was 12% versus a livelihood average of 16% "
        "(weak signal), 95% CI 9%-15%, n=42."
    )
    monkeypatch.setattr(
        writer,
        "_generate_rewrites",
        lambda statements: ["Demand was 12% versus a livelihood average of 16%."],
    )

    result = writer.rewrite_factors([{"text": source, "source": "Survey"}])

    assert result[0]["text"] == (
        "Demand was 12% versus a livelihood average of 16%."
    )
    assert result[0]["evidence"] == source
    assert result[0]["strength"] == "weak"


def test_weak_risk_fact_is_not_shown_as_an_opportunity():
    source_factors = [
        {
            "category": "opportunities",
            "scope": "risk",
            "text": "Possible upside from lower flood exposure (weak signal)",
            "similarity": 0.9,
        },
        {
            "category": "opportunities",
            "scope": "risk",
            "text": "Clear risk-related opportunity",
            "similarity": 0.8,
        },
        {
            "category": "opportunities",
            "scope": "market",
            "text": "Possible market opportunity (weak signal)",
            "similarity": 0.7,
        },
    ]

    result = scoring.score_factors(source_factors, {})

    assert [item["text"] for item in result] == [
        "Clear risk-related opportunity",
        "Possible market opportunity (weak signal)",
    ]


def test_build_swot_keeps_existing_public_shape(monkeypatch):
    source_factors = [
        {
            "category": "opportunities",
            "text": "Demand is growing.",
            "source": "Survey",
            "district": None,
            "is_estimated": False,
        }
    ]
    monkeypatch.setattr(
        swot,
        "get_livelihood_factors",
        lambda livelihood, district=None: source_factors,
    )
    monkeypatch.setattr(swot, "rewrite_factors", lambda selected: selected)

    result = swot.build_swot("TRADE", {"district": "Badulla"})

    assert set(result) == SWOT_KEYS
    assert result["opportunities"] == [
        {
            "text": "Demand is growing.",
            "source": "Survey",
            "evidence": "Demand is growing.",
            "strength": "clear",
        }
    ]
