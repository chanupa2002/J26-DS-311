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
from app.components.livelihood_planning.decision_trail import build_swot_trail

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


class FilteringQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def in_(self, column, values):
        self.filters.append(lambda row: row.get(column) in values)
        return self

    def eq(self, column, value):
        self.filters.append(lambda row: row.get(column) == value)
        return self

    def execute(self):
        rows = [
            row
            for row in self.rows
            if all(predicate(row) for predicate in self.filters)
        ]
        return SimpleNamespace(data=rows)


class FilteringSupabase:
    def __init__(self, tables):
        self.tables = tables
        self.table_calls = []

    def table(self, name):
        self.table_calls.append(name)
        return FilteringQuery(self.tables.get(name, []))

    def rpc(self, name, params):
        raise AssertionError("Vector search must not run for viability previews.")


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


def test_viability_previews_use_fact_evidence_and_no_model_2_services(
    monkeypatch,
):
    score_rows = [
        {
            "livelihood": "TRADE",
            "district": "Badulla",
            "viability": 70,
            "viability_low": 65,
            "viability_high": 75,
            "profitability": 60,
            "market": 65,
            "area": 80,
            "resilience": 75,
            "confidence": 0.8,
        },
        {
            "livelihood": "LIVESTOCK & ANIMAL HUSBANDRY",
            "district": "Monaragala",
            "viability": 62,
            "viability_low": 56,
            "viability_high": 68,
            "profitability": 60,
            "market": 61,
            "area": 63,
            "resilience": 64,
            "confidence": 0.7,
        },
    ]

    database = FilteringSupabase(
        {
            "livelihood_scores": score_rows,
            "livelihood_facts": [
                {
                    "scope": "viability",
                    "livelihood": "TRADE",
                    "district": "Badulla",
                    "is_estimated": False,
                }
            ],
        }
    )
    monkeypatch.setattr(scoring, "get_supabase", lambda: database)
    monkeypatch.setattr(
        factors,
        "_embed_query",
        lambda query: (_ for _ in ()).throw(
            AssertionError("Embedding must not run for previews.")
        ),
    )
    monkeypatch.setattr(
        writer,
        "_generate_rewrites",
        lambda statements: (_ for _ in ()).throw(
            AssertionError("Gemini must not run for previews.")
        ),
    )

    result = scoring.get_viability_previews(
        [
            "TRADE",
            "LIVESTOCK & ANIMAL HUSBANDRY",
            "AGRICULTURE & PLANTATION CROPS",
        ],
        "Badulla",
    )

    assert database.table_calls == [
        "livelihood_scores",
        "livelihood_facts",
        "livelihood_facts",
    ]
    assert len(result) == 3
    assert result[0] == {
        "livelihood": "TRADE",
        "score": 70.0,
        "low": 65.0,
        "high": 75.0,
        "estimated": False,
    }
    assert result[1]["estimated"] is True
    assert result[2] is None


def test_viability_preview_estimated_matches_detailed_viability(monkeypatch):
    score_rows = [
        {
            "livelihood": livelihood,
            "district": "Badulla",
            "viability": score,
            "viability_low": score - 5,
            "viability_high": score + 5,
            "profitability": score,
            "market": score,
            "area": score,
            "resilience": score,
            "confidence": 0.8,
        }
        for livelihood, score in (
            ("TRADE", 70),
            ("LIVESTOCK & ANIMAL HUSBANDRY", 62),
        )
    ]
    database = FilteringSupabase(
        {
            "livelihood_scores": score_rows,
            "livelihood_facts": [
                {
                    "scope": "viability",
                    "livelihood": "TRADE",
                    "district": "Badulla",
                    "is_estimated": False,
                }
            ],
        }
    )
    monkeypatch.setattr(scoring, "get_supabase", lambda: database)
    livelihoods = ["TRADE", "LIVESTOCK & ANIMAL HUSBANDRY"]

    previews = scoring.get_viability_previews(livelihoods, "Badulla")
    details = [
        scoring.get_viability(livelihood, "Badulla")
        for livelihood in livelihoods
    ]

    assert [preview["estimated"] for preview in previews] == [
        detail["estimated"] for detail in details
    ] == [False, True]


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


def test_swot_trail_counts_fetched_and_selected_facts(monkeypatch):
    source_factors = [
        {
            "category": "strengths",
            "text": "Local demand was observed.",
            "source": "Survey",
            "district": "Badulla",
            "is_estimated": False,
            "similarity": 0.8,
            "n_obs": 24,
        },
        {
            "category": "opportunities",
            "text": "Wider demand may grow.",
            "source": "Survey",
            "district": None,
            "is_estimated": True,
            "similarity": 0.6,
            "n_obs": 18,
        },
    ]
    monkeypatch.setattr(
        swot,
        "get_livelihood_factors",
        lambda livelihood, district=None: source_factors,
    )
    monkeypatch.setattr(
        swot,
        "rewrite_factors",
        lambda selected: [
            {
                **factor,
                "evidence": factor["text"],
                "strength": "clear",
                "_decision_was_reworded": False,
                "_decision_number_check_passed": True,
            }
            for factor in selected
        ],
    )
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

    result = swot.build_swot_report("TRADE", {"district": "Badulla"})

    steps = result["decision_trail"]["steps"]
    assert all(len(step["summary"].split()) <= 25 for step in steps)
    facts = next(step for step in steps if step["id"] == "swot-facts")
    selection = next(step for step in steps if step["id"] == "swot-selection")
    public_point_count = sum(len(items) for items in result["swot"].values())
    assert facts["details"] == {
        "facts_found": 2,
        "district_facts": 1,
        "estimated_facts": 1,
    }
    assert facts["summary"] == (
        "1 of 2 facts is from this district. "
        "The rest come from wider district data."
    )
    assert len(selection["details"]["points"]) == public_point_count == 2
    assert selection["summary"] == (
        "Points were chosen by how closely they match this livelihood and "
        "district; local evidence was preferred."
    )
    assert selection["details"]["points"][0]["source"] == "Survey"
    assert selection["details"]["points"][0]["records"] == 24
    assert selection["details"]["points"][0]["chosen_because"] == (
        "Closest match by meaning"
    )
    request = next(step for step in steps if step["id"] == "swot-request")
    scope = next(step for step in steps if step["id"] == "swot-scope")
    wording = next(step for step in steps if step["id"] == "swot-wording")
    viability = next(step for step in steps if step["id"] == "swot-viability")
    confidence = next(step for step in steps if step["id"] == "swot-confidence")
    assert request["details"]["livelihood"] == "Trade"
    assert scope["details"]["livelihood"] == "Trade"
    assert scope["summary"] == (
        "This SWOT describes the livelihood in this district. "
        "Personal fit comes from the recommendation step."
    )
    assert wording["summary"] == (
        "2 sentences were checked against their source facts. "
        "0 sentences were reworded; 2 sentences kept the original wording."
    )
    assert viability["summary"] == (
        "The viability result is based on wider district evidence. "
        "Not enough records came from this exact district."
    )
    assert confidence["summary"] == (
        "Evidence supports this result. Needs a local check because "
        "exact-district records are limited. Every point shows its source "
        "and the supporting record count."
    )
    assert result["confidence"] == "low"
    assert facts["flag"] == "note"
    assert viability["flag"] == "note"
    assert confidence["flag"] == "warning"


@pytest.mark.parametrize(
    ("similarities", "expected_summary", "expected_reasons"),
    [
        (
            [0.8, None],
            "1 of 2 points was matched by meaning; the rest were chosen "
            "because they describe this district or the wider area.",
            ["Closest match by meaning", "Describes the wider area"],
        ),
        (
            [None, None],
            "Points were chosen because they describe this livelihood in "
            "this district or the wider area.",
            ["Describes this district", "Describes the wider area"],
        ),
    ],
)
def test_swot_selection_explains_available_match_scores(
    similarities, expected_summary, expected_reasons
):
    selected_factors = [
        {
            "category": "strengths",
            "text": f"Fact {index}",
            "source": "Survey",
            "district": "Badulla" if index == 0 else None,
            "is_estimated": False,
            "similarity": similarity,
            "score": similarity if similarity is not None else 0.0,
            "n_obs": 20,
        }
        for index, similarity in enumerate(similarities)
    ]

    trail = build_swot_trail(
        livelihood="TRADE",
        district="Badulla",
        factors=selected_factors,
        selected_factors=selected_factors,
        written_factors=[],
        viability_record={
            "score": 70.0,
            "low": 65.0,
            "high": 75.0,
            "profitability": 60.0,
            "market": 65.0,
            "area": 80.0,
            "resilience": 75.0,
            "confidence": 0.8,
            "estimated": False,
        },
        confidence="normal",
        district_missing=False,
        district_unknown=False,
    )

    selection = next(
        step for step in trail["steps"] if step["id"] == "swot-selection"
    )
    assert selection["summary"] == expected_summary
    assert [
        point["chosen_because"] for point in selection["details"]["points"]
    ] == expected_reasons
    assert all(
        "ranking_score" in point
        for point in selection["details"]["points"]
    )
