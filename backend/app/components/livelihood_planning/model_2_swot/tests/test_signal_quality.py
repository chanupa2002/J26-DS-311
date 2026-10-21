"""Tests for Model 2 weak-signal ranking and missing-category notes."""

import logging
import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.components.livelihood_planning.model_2_swot import (
    gemini_client,
    grounding,
    scoring,
    swot,
    writer,
)


class _FakeGeminiError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def _install_fake_genai_types(monkeypatch):
    fake_genai = ModuleType("google.genai")
    fake_genai.types = SimpleNamespace(
        GenerateContentConfig=lambda **kwargs: kwargs
    )
    fake_google = ModuleType("google")
    fake_google.genai = fake_genai
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)


def _mock_writer_client(monkeypatch, side_effects):
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs["model"])
            result = side_effects.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

    monkeypatch.setattr(
        writer,
        "create_gemini_client",
        lambda: SimpleNamespace(models=FakeModels()),
    )
    monkeypatch.setattr(writer, "get_gemini_text_model", lambda: "primary-model")
    monkeypatch.setattr(writer, "_load_project_dotenv", lambda: None)
    return calls


class _FilteredQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def execute(self):
        rows = [
            row
            for row in self.rows
            if all(row.get(column) == value for column, value in self.filters)
        ]
        return SimpleNamespace(data=rows)


class _ViabilitySupabase:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _FilteredQuery(self.tables.get(name, []))


def _complete_swot():
    return {
        category: [{"text": category, "source": "Survey"}]
        for category in swot.SWOT_KEYS
    }


def _viability_score_row():
    return {
        "livelihood": "TRADE",
        "district": "Badulla",
        "viability": 70.0,
        "viability_low": 65.0,
        "viability_high": 75.0,
        "profitability": 60.0,
        "market": 65.0,
        "area": 80.0,
        "resilience": 75.0,
        "confidence": 0.8,
    }


def test_district_viability_evidence_is_not_estimated(monkeypatch):
    client = _ViabilitySupabase(
        {
            "livelihood_scores": [_viability_score_row()],
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
    monkeypatch.setattr(scoring, "get_supabase", lambda: client)
    monkeypatch.setattr(swot, "build_swot", lambda *args: _complete_swot())

    result = swot.build_swot_report("TRADE", {"district": "Badulla"})

    assert result["viability"]["estimated"] is False
    assert swot.ESTIMATED_VIABILITY_NOTE not in result["notes"]
    assert result["confidence"] == "normal"


def test_missing_district_viability_evidence_is_low_confidence(monkeypatch):
    client = _ViabilitySupabase(
        {
            "livelihood_scores": [_viability_score_row()],
            "livelihood_facts": [],
        }
    )
    monkeypatch.setattr(scoring, "get_supabase", lambda: client)
    monkeypatch.setattr(swot, "build_swot", lambda *args: _complete_swot())

    result = swot.build_swot_report("TRADE", {"district": "Badulla"})

    assert result["viability"]["estimated"] is True
    assert swot.ESTIMATED_VIABILITY_NOTE in result["notes"]
    assert result["confidence"] == "low"


def test_writer_retries_503_then_succeeds(monkeypatch, caplog):
    _install_fake_genai_types(monkeypatch)
    calls = _mock_writer_client(
        monkeypatch,
        [
            _FakeGeminiError(503, "temporarily unavailable"),
            SimpleNamespace(text='["Rewritten fact."]'),
        ],
    )
    waits = []
    monkeypatch.setattr(writer.time, "sleep", waits.append)
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "fallback-model")

    with caplog.at_level(logging.INFO):
        result = writer.rewrite_factors(
            [{"text": "Original fact.", "source": "Survey"}]
        )

    assert result[0]["text"] == "Rewritten fact."
    assert calls == ["primary-model", "primary-model"]
    assert waits == [1.0]
    assert "Gemini rewrite model used: primary-model" in caplog.messages


def test_writer_skips_404_model_and_uses_fallback(monkeypatch, caplog):
    _install_fake_genai_types(monkeypatch)
    calls = _mock_writer_client(
        monkeypatch,
        [
            _FakeGeminiError(404, "model not available"),
            SimpleNamespace(text='["Fallback rewrite."]'),
        ],
    )
    waits = []
    monkeypatch.setattr(writer.time, "sleep", waits.append)
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "fallback-model")

    with caplog.at_level(logging.INFO):
        result = writer.rewrite_factors(
            [{"text": "Original fact.", "source": "Survey"}]
        )

    assert result[0]["text"] == "Fallback rewrite."
    assert calls == ["primary-model", "fallback-model"]
    assert waits == []
    assert "Gemini rewrite model used: fallback-model" in caplog.messages


def test_writer_all_models_fail_within_total_time_cap(monkeypatch, caplog):
    _install_fake_genai_types(monkeypatch)
    calls = _mock_writer_client(
        monkeypatch,
        [_FakeGeminiError(503, "service unavailable") for _ in range(9)],
    )
    clock = {"now": 0.0}

    def fake_sleep(seconds):
        clock["now"] += seconds

    monkeypatch.setattr(writer.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(writer.time, "sleep", fake_sleep)
    monkeypatch.setenv(
        "GEMINI_FALLBACK_MODELS", "fallback-one,fallback-two"
    )

    with caplog.at_level(logging.WARNING):
        result = writer.rewrite_factors(
            [{"text": "Original fact.", "source": "Survey"}]
        )

    assert result[0]["text"] == "Original fact."
    assert calls == [
        "primary-model",
        "primary-model",
        "primary-model",
        "primary-model",
        "fallback-one",
        "fallback-one",
        "fallback-one",
        "fallback-one",
        "fallback-two",
    ]
    assert clock["now"] == pytest.approx(15.0)
    assert any(
        "TimeoutError" in message and "15-second limit" in message
        for message in caplog.messages
    )


def test_weak_signal_penalty_applies_before_top_three_cap():
    factors = [
        {
            "category": "strengths",
            "text": "Estimated demand (weak signal)",
            "similarity": 0.75,
        },
        {"category": "strengths", "text": "Clear signal A", "similarity": 0.70},
        {"category": "strengths", "text": "Clear signal B", "similarity": 0.65},
        {"category": "strengths", "text": "Clear signal C", "similarity": 0.60},
    ]

    result = scoring.score_factors(factors, {})

    assert len(result) == 3
    assert [factor["text"] for factor in result] == [
        "Clear signal A",
        "Clear signal B",
        "Clear signal C",
    ]


def test_empty_swot_category_adds_note_without_inventing_item(monkeypatch):
    swot_result = {
        "strengths": [{"text": "Strength", "source": "Survey"}],
        "weaknesses": [{"text": "Weakness", "source": "Survey"}],
        "opportunities": [],
        "threats": [{"text": "Threat", "source": "Survey"}],
    }
    monkeypatch.setattr(swot, "build_swot", lambda livelihood, features: swot_result)
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
            "estimated": False,
        },
    )

    result = swot.build_swot_report("TRADE", {"district": "Badulla"})

    assert result["swot"]["opportunities"] == []
    assert (
        "No clear opportunity signal was found in the data for this livelihood "
        "and district."
    ) in result["notes"]


def test_fallbacks_log_one_sanitized_warning_with_reason(
    monkeypatch, caplog
):
    secret = "test-secret-key"
    stray_secret = "stray-google-key"
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    monkeypatch.setenv("GOOGLE_API_KEY", stray_secret)
    monkeypatch.setattr(
        writer,
        "_generate_rewrites",
        lambda statements: (_ for _ in ()).throw(
            RuntimeError(
                f"service unavailable for {secret} and {stray_secret}"
            )
        ),
    )

    with caplog.at_level(logging.WARNING):
        writer.rewrite_factors(
            [{"text": "Observed viability was 57.4.", "source": "Survey"}]
        )

    writer_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == writer.__name__
    ]
    assert writer_messages == [
        "Falling back to original fact text: RuntimeError: service unavailable "
        "for [REDACTED] and [REDACTED]"
    ]
    assert secret not in writer_messages[0]
    assert stray_secret not in writer_messages[0]

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        grounding.grounded_or_original(
            "Observed viability was 58.", "Observed viability was 57.4."
        )

    grounding_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == grounding.__name__
    ]
    assert grounding_messages == [
        "Falling back to original fact text: ungrounded number: 58."
    ]


def test_project_dotenv_values_create_explicitly_keyed_client(monkeypatch):
    loaded = {}
    fake_dotenv = ModuleType("dotenv")

    def fake_load_dotenv(dotenv_path, override):
        loaded["path"] = dotenv_path
        loaded["override"] = override
        monkeypatch.setenv("GEMINI_API_KEY", "project-env-key")
        monkeypatch.setenv("GEMINI_TEXT_MODEL", "project-text-model")

    fake_dotenv.load_dotenv = fake_load_dotenv
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setattr(gemini_client, "_settings_value", lambda name: None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_TEXT_MODEL", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "stray-google-key")

    captured = {}
    fake_genai = SimpleNamespace(
        Client=lambda **kwargs: captured.update(kwargs) or object()
    )
    fake_google = ModuleType("google")
    fake_google.genai = fake_genai
    monkeypatch.setitem(sys.modules, "google", fake_google)

    gemini_client.create_gemini_client()

    assert loaded == {
        "path": gemini_client.BACKEND_ENV_PATH,
        "override": False,
    }
    assert gemini_client.BACKEND_ENV_PATH.name == ".env"
    assert gemini_client.BACKEND_ENV_PATH.parent.name == "backend"
    assert captured == {"api_key": "project-env-key"}
    assert captured["api_key"] != "stray-google-key"
    assert gemini_client.get_gemini_text_model() == "project-text-model"
