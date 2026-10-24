"""API tests for the livelihood-planning endpoints."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.components.livelihood_planning import router as router_module
from app.components.livelihood_planning.decision_trail import (
    format_livelihood_name,
)
from app.components.livelihood_planning.model_2_swot import (
    factors as model_2_factors,
    scoring as model_2_scoring,
    swot as model_2_swot,
    writer as model_2_writer,
)

app = FastAPI()
app.include_router(router_module.router)
client = TestClient(app)

EMPTY_SWOT = {
    "strengths": [],
    "weaknesses": [],
    "opportunities": [],
    "threats": [],
}
VIABILITY = {
    "score": 70.0,
    "low": 65.0,
    "high": 75.0,
    "profitability": 60.0,
    "market": 65.0,
    "area": 80.0,
    "resilience": 75.0,
    "estimated": False,
}
RECOMMENDATIONS = [
    {"livelihood": "TRADE", "score": 0.7, "reasons": []},
    {
        "livelihood": "LIVESTOCK & ANIMAL HUSBANDRY",
        "score": 0.2,
        "reasons": [],
    },
    {
        "livelihood": "AGRICULTURE & PLANTATION CROPS",
        "score": 0.1,
        "reasons": [],
    },
]
VIABILITY_PREVIEW = [
    {
        "livelihood": "TRADE",
        "score": 70.0,
        "low": 65.0,
        "high": 75.0,
        "estimated": False,
    },
    {
        "livelihood": "LIVESTOCK & ANIMAL HUSBANDRY",
        "score": 62.0,
        "low": 56.0,
        "high": 68.0,
        "estimated": False,
    },
    None,
]
RECOMMENDATION_TRAIL = {
    "steps": [
        {
            "id": "recommendation-inputs",
            "title": "What we looked at",
            "summary": "Household details and area values for Badulla were used.",
            "flag": "ok",
            "details": {},
        }
    ]
}
SWOT_TRAIL = {
    "steps": [
        {
            "id": "swot-request",
            "title": "What we asked",
            "summary": "Model 2 reviewed Trade for Badulla.",
            "flag": "ok",
            "details": {},
        }
    ]
}
DECISION_TRAIL = {
    "version": 1,
    "recommendation": RECOMMENDATION_TRAIL,
    "swot": SWOT_TRAIL,
}


def _swot_response():
    return {
        "recommendations": RECOMMENDATIONS,
        "swot": EMPTY_SWOT,
        "viability": VIABILITY,
        "confidence": "normal",
        "notes": ["Model note"],
        "placeholder": False,
        "selected_livelihood": "TRADE",
        "viability_preview": VIABILITY_PREVIEW,
        "decision_trail": DECISION_TRAIL,
    }


class FakeQuery:
    def __init__(self, database, table_name):
        self.database = database
        self.table_name = table_name
        self.selected = "*"
        self.filters = []
        self.limit_count = None
        self.ordering = None
        self.insert_payload = None
        self.in_filters = []

    def select(self, columns):
        self.selected = columns
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def in_(self, column, values):
        self.in_filters.append((column, values))
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def order(self, column, desc=False):
        self.ordering = (column, desc)
        return self

    def insert(self, payload):
        self.insert_payload = payload
        return self

    def execute(self):
        if self.insert_payload is not None:
            self.database.last_insert = dict(self.insert_payload)
            record = {
                "id": f"assessment-{len(self.database.tables.get(self.table_name, [])) + 1}",
                **self.insert_payload,
                "created_at": "2026-10-21T10:00:00Z",
            }
            self.database.tables.setdefault(self.table_name, []).append(record)
            return SimpleNamespace(data=[record])

        rows = [dict(row) for row in self.database.tables.get(self.table_name, [])]
        rows = [
            row
            for row in rows
            if all(str(row.get(column)) == str(value) for column, value in self.filters)
        ]
        rows = [
            row
            for row in rows
            if all(row.get(column) in values for column, values in self.in_filters)
        ]
        if self.ordering:
            column, descending = self.ordering
            rows.sort(key=lambda row: row.get(column) or "", reverse=descending)
        if self.limit_count is not None:
            rows = rows[: self.limit_count]
        if self.selected != "*":
            columns = self.selected.split(",")
            rows = [
                {column: row.get(column) for column in columns}
                for row in rows
            ]
        return SimpleNamespace(data=rows)


class FakeSupabase:
    def __init__(self, tables=None):
        self.tables = tables or {}
        self.last_insert = None

    def table(self, name):
        return FakeQuery(self, name)


class UnavailableSupabase:
    def table(self, name):
        raise ConnectionError("raw database connection details")


class InsertFailureSupabase(FakeSupabase):
    def table(self, name):
        if name == "livelihood_assessments":
            raise ConnectionError("raw insert failure details")
        return super().table(name)


def _assessment_record(record_id, created_at):
    return {
        "id": record_id,
        "beneficiary_id": "beneficiary-1",
        "input_snapshot": {"district": "Badulla"},
        "recommendations": _swot_response()["recommendations"],
        "chosen_livelihood": "TRADE",
        "swot": EMPTY_SWOT,
        "viability": VIABILITY,
        "notes": [],
        "confidence": "normal",
        "status": "draft",
        "created_at": created_at,
    }


def test_health_endpoint():
    response = client.get("/api/livelihood/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_recommend_endpoint(monkeypatch):
    monkeypatch.setattr(
        router_module.services,
        "get_viability_previews",
        lambda livelihoods, district: [None for _ in livelihoods],
    )
    response = client.post("/api/livelihood/recommend", json={})

    assert response.status_code == 200
    assert len(response.json()["recommendations"]) == 3
    assert response.json()["placeholder"] is False


def test_recommend_keeps_old_keys_and_adds_explanation_fields(monkeypatch):
    monkeypatch.setattr(
        router_module.services,
        "get_viability_previews",
        lambda livelihoods, district: [None for _ in livelihoods],
    )
    response = client.post(
        "/api/livelihood/recommend",
        json={
            "district": "Badulla",
            "ds_division": "Mahiyanganaya",
            "age": 36,
            "gender": "Female",
            "female_headed": True,
            "disability": False,
            "aswesuma_category": "Poor",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert {"recommendations", "placeholder"}.issubset(body)
    assert body["confidence"] in {"low", "normal"}
    assert isinstance(body["notes"], list)
    assert body["viability_preview"] == [None, None, None]
    assert body["decision_trail"]["version"] == 1
    recommendation_steps = body["decision_trail"]["recommendation"]["steps"]
    assert [step["id"] for step in recommendation_steps] == [
        "recommendation-inputs",
        "recommendation-scoring",
        "recommendation-top3",
        "recommendation-confidence",
    ]
    assert all(len(step["summary"].split()) <= 25 for step in recommendation_steps)
    scoring = recommendation_steps[1]["details"]
    assert len(scoring["scores"]) == 9
    assert sum(item["percentage"] for item in scoring["scores"]) == pytest.approx(
        100.0, abs=0.01
    )
    top_three = recommendation_steps[2]["details"]["recommendations"]
    assert [item["livelihood"] for item in top_three] == [
        format_livelihood_name(item["livelihood"])
        for item in body["recommendations"]
    ]
    assert recommendation_steps[1]["summary"].startswith(
        "9 livelihood options were compared;"
    )
    assert [item["percentage"] for item in top_three] == pytest.approx(
        [item["score"] * 100 for item in body["recommendations"]], abs=0.01
    )
    assert all(isinstance(note, str) for note in body["notes"])
    for recommendation in body["recommendations"]:
        assert {"livelihood", "score"}.issubset(recommendation)
        assert isinstance(recommendation["reasons"], list)


@pytest.mark.parametrize("age", [-1, 121])
def test_request_rejects_age_outside_valid_range(age):
    response = client.post("/api/livelihood/recommend", json={"age": age})

    assert response.status_code == 422


def test_swot_endpoint(monkeypatch):
    seen = {}

    def fake_build_swot_response(features):
        seen["features"] = features
        return _swot_response()

    monkeypatch.setattr(
        router_module.services,
        "build_swot_response",
        fake_build_swot_response,
    )
    response = client.post(
        "/api/livelihood/swot", json={"district": "Badulla"}
    )

    assert response.status_code == 200
    assert response.json() == _swot_response()
    assert seen["features"] == {"district": "Badulla"}


def test_build_swot_response_preserves_existing_behavior(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        router_module.services,
        "recommend_with_context",
        lambda features: {
            "recommendations": _swot_response()["recommendations"],
            "confidence": "normal",
            "notes": ["Shared note", "Model 1 note"],
            "decision_trail": {
                "version": 1,
                "recommendation": RECOMMENDATION_TRAIL,
            },
        },
    )
    monkeypatch.setattr(
        router_module.services,
        "build_swot_report",
        lambda livelihood, features: seen.update(
            {"livelihood": livelihood, "features": features}
        )
        or {
            "swot": EMPTY_SWOT,
            "viability": VIABILITY,
            "confidence": "low",
            "notes": ["Shared note", "Model 2 note"],
            "decision_trail": SWOT_TRAIL,
        },
    )
    monkeypatch.setattr(
        router_module.services,
        "get_viability_previews",
        lambda livelihoods, district: VIABILITY_PREVIEW,
    )

    result = router_module.services.build_swot_response(
        {"district": "Badulla"}
    )

    assert result == {
        "recommendations": _swot_response()["recommendations"],
        "swot": EMPTY_SWOT,
        "viability": VIABILITY,
        "confidence": "low",
        "notes": ["Shared note", "Model 1 note", "Model 2 note"],
        "placeholder": False,
        "selected_livelihood": "TRADE",
        "viability_preview": VIABILITY_PREVIEW,
        "decision_trail": DECISION_TRAIL,
    }
    assert seen == {
        "livelihood": "TRADE",
        "features": {"district": "Badulla"},
    }


def test_selected_top_three_livelihood_builds_its_swot_and_trail(monkeypatch):
    selected_trail = {
        "steps": [
            {
                "id": "swot-request",
                "title": "What we asked",
                "summary": "Model 2 reviewed Livestock for Badulla.",
                "flag": "ok",
                "details": {},
            }
        ]
    }
    selected_swot = {
        **EMPTY_SWOT,
        "strengths": [
            {
                "text": "Livestock has local demand.",
                "source": "Survey",
                "evidence": "Livestock has local demand.",
                "strength": "clear",
            }
        ],
    }
    monkeypatch.setattr(
        router_module.services,
        "recommend_with_context",
        lambda features: {
            "recommendations": RECOMMENDATIONS,
            "confidence": "normal",
            "notes": [],
            "decision_trail": {
                "version": 1,
                "recommendation": RECOMMENDATION_TRAIL,
            },
        },
    )
    monkeypatch.setattr(
        router_module.services,
        "get_viability_previews",
        lambda livelihoods, district: VIABILITY_PREVIEW,
    )
    monkeypatch.setattr(
        router_module.services,
        "build_swot_report",
        lambda livelihood, features: {
            "swot": selected_swot,
            "viability": VIABILITY,
            "confidence": "normal",
            "notes": [],
            "decision_trail": selected_trail,
        },
    )

    response = client.post(
        "/api/livelihood/swot",
        json={
            "district": "Badulla",
            "livelihood": "livestock and animal husbandry",
        },
    )
    result = response.json()

    assert response.status_code == 200
    assert result["selected_livelihood"] == (
        "LIVESTOCK & ANIMAL HUSBANDRY"
    )
    assert result["swot"] == selected_swot
    assert result["decision_trail"]["recommendation"] == RECOMMENDATION_TRAIL
    assert result["decision_trail"]["swot"] == selected_trail


def test_livelihood_outside_top_three_returns_clear_422(monkeypatch):
    monkeypatch.setattr(
        router_module.services,
        "recommend_with_context",
        lambda features: {
            "recommendations": RECOMMENDATIONS,
            "confidence": "normal",
            "notes": [],
            "decision_trail": {
                "version": 1,
                "recommendation": RECOMMENDATION_TRAIL,
            },
        },
    )
    monkeypatch.setattr(
        router_module.services,
        "get_viability_previews",
        lambda livelihoods, district: VIABILITY_PREVIEW,
    )

    response = client.post(
        "/api/livelihood/swot",
        json={"district": "Badulla", "livelihood": "OTHER"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Livelihood must be one of the Model 1 top 3: "
        "TRADE, LIVESTOCK & ANIMAL HUSBANDRY, "
        "AGRICULTURE & PLANTATION CROPS."
    )


def test_swot_unknown_district_survives_model_2_supabase_failure(
    monkeypatch,
):
    monkeypatch.setattr(
        router_module.services,
        "recommend_with_context",
        lambda features: {
            "recommendations": _swot_response()["recommendations"],
            "confidence": "normal",
            "notes": [],
            "decision_trail": {
                "version": 1,
                "recommendation": RECOMMENDATION_TRAIL,
            },
        },
    )
    monkeypatch.setattr(
        model_2_factors,
        "get_supabase",
        lambda: (_ for _ in ()).throw(ConnectionError("offline")),
    )
    monkeypatch.setattr(
        model_2_scoring,
        "get_supabase",
        lambda: (_ for _ in ()).throw(ConnectionError("offline")),
    )

    response = client.post(
        "/api/livelihood/swot", json={"district": "Unknown District"}
    )

    assert response.status_code == 200
    assert response.json()["confidence"] == "low"
    assert any(
        "district-level monitoring" in note
        for note in response.json()["notes"]
    )


def test_list_beneficiaries(monkeypatch):
    database = FakeSupabase(
        {
            "beneficiaries": [
                {
                    "id": "beneficiary-1",
                    "full_name": "Demo Person",
                    "district": "Badulla",
                    "age": 36,
                    "gender": "Female",
                    "female_headed": True,
                    "disability": False,
                    "aswesuma_category": "Poor",
                    "is_demo": True,
                }
            ]
        }
    )
    monkeypatch.setattr(router_module, "get_supabase", lambda: database)

    response = client.get("/api/livelihood/beneficiaries")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "beneficiary-1",
            "full_name": "Demo Person",
            "district": "Badulla",
            "age": 36,
            "gender": "Female",
            "female_headed": True,
            "disability": False,
            "aswesuma_category": "Poor",
            "is_demo": True,
        }
    ]


def test_list_beneficiaries_returns_missing_values_as_null(monkeypatch):
    database = FakeSupabase(
        {
            "beneficiaries": [
                {
                    "id": "beneficiary-2",
                    "full_name": "Demo Person Two",
                    "district": None,
                    "age": None,
                    "gender": None,
                }
            ]
        }
    )
    monkeypatch.setattr(router_module, "get_supabase", lambda: database)

    response = client.get("/api/livelihood/beneficiaries")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "beneficiary-2",
            "full_name": "Demo Person Two",
            "district": None,
            "age": None,
            "gender": None,
            "female_headed": None,
            "disability": None,
            "aswesuma_category": None,
            "is_demo": None,
        }
    ]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/livelihood/beneficiaries"),
        ("post", "/api/livelihood/assess/beneficiary-1"),
        ("get", "/api/livelihood/assessments/beneficiary-1"),
    ],
)
def test_database_endpoints_return_clean_503(monkeypatch, method, path):
    monkeypatch.setattr(
        router_module, "get_supabase", lambda: UnavailableSupabase()
    )

    response = getattr(client, method)(path)

    assert response.status_code == 503
    assert response.json() == {
        "detail": router_module.DATABASE_UNAVAILABLE_MESSAGE
    }
    assert "raw database" not in response.text


def test_assess_beneficiary_saves_draft_without_name(monkeypatch):
    database = FakeSupabase(
        {
            "beneficiaries": [
                {
                    "id": "beneficiary-1",
                    "full_name": "Private Name",
                    "district": "Badulla",
                    "ds_division": None,
                    "age": 36,
                    "gender": "Female",
                    "female_headed": True,
                    "disability": False,
                    "aswesuma_category": "Poor",
                    "is_demo": True,
                }
            ]
        }
    )
    seen = {}

    def fake_build_swot_response(features):
        seen["features"] = features
        return _swot_response()

    monkeypatch.setattr(router_module, "get_supabase", lambda: database)
    monkeypatch.setattr(
        router_module.services,
        "build_swot_response",
        fake_build_swot_response,
    )

    response = client.post("/api/livelihood/assess/beneficiary-1")

    expected_features = {
        "district": "Badulla",
        "age": 36,
        "gender": "Female",
        "female_headed": True,
        "disability": False,
        "aswesuma_category": "Poor",
    }
    assert response.status_code == 200
    assert seen["features"] == expected_features
    assert database.last_insert["input_snapshot"] == expected_features
    assert "full_name" not in database.last_insert["input_snapshot"]
    assert database.last_insert["recommendations"] == (
        _swot_response()["recommendations"]
    )
    assert database.last_insert["chosen_livelihood"] == "TRADE"
    assert database.last_insert["swot"] == EMPTY_SWOT
    assert database.last_insert["viability"] == VIABILITY
    assert database.last_insert["notes"] == ["Model note"]
    assert database.last_insert["confidence"] == "normal"
    assert database.last_insert["decision_trail"] == DECISION_TRAIL
    assert database.last_insert["status"] == "draft"
    assert "selected_livelihood" not in database.last_insert
    assert "viability_preview" not in database.last_insert
    assert response.json()["status"] == "draft"
    assert response.json()["selected_livelihood"] == "TRADE"
    assert response.json()["viability_preview"] == VIABILITY_PREVIEW
    assert response.json()["decision_trail"] == DECISION_TRAIL

    history = client.get("/api/livelihood/assessments/beneficiary-1")
    assert history.status_code == 200
    assert history.json()[0]["decision_trail"] == DECISION_TRAIL


def test_assess_accepts_optional_selected_livelihood(monkeypatch):
    database = FakeSupabase(
        {
            "beneficiaries": [
                {
                    "id": "beneficiary-1",
                    "full_name": "Private Name",
                    "district": "Badulla",
                    "ds_division": "Passara",
                    "age": 38,
                    "gender": "Female",
                    "female_headed": True,
                    "disability": False,
                    "aswesuma_category": "Poor",
                    "is_demo": True,
                }
            ]
        }
    )
    seen = {}

    def fake_build_swot_response(features, requested_livelihood):
        seen["features"] = features
        seen["livelihood"] = requested_livelihood
        return {
            **_swot_response(),
            "selected_livelihood": "LIVESTOCK & ANIMAL HUSBANDRY",
        }

    monkeypatch.setattr(router_module, "get_supabase", lambda: database)
    monkeypatch.setattr(
        router_module.services,
        "build_swot_response",
        fake_build_swot_response,
    )

    response = client.post(
        "/api/livelihood/assess/beneficiary-1",
        json={"livelihood": "livestock and animal husbandry"},
    )

    assert response.status_code == 200
    assert seen["livelihood"] == "livestock and animal husbandry"
    assert seen["features"]["district"] == "Badulla"
    assert response.json()["selected_livelihood"] == (
        "LIVESTOCK & ANIMAL HUSBANDRY"
    )
    assert database.last_insert["chosen_livelihood"] == "TRADE"


def test_assess_rejects_livelihood_outside_top_three(monkeypatch):
    database = FakeSupabase(
        {
            "beneficiaries": [
                {
                    "id": "beneficiary-1",
                    "full_name": "Private Name",
                    "district": "Badulla",
                }
            ]
        }
    )

    def reject_selection(features, requested_livelihood):
        raise router_module.services.InvalidLivelihoodSelection(
            "Livelihood must be one of the Model 1 top 3: "
            "TRADE, LIVESTOCK & ANIMAL HUSBANDRY, "
            "AGRICULTURE & PLANTATION CROPS."
        )

    monkeypatch.setattr(router_module, "get_supabase", lambda: database)
    monkeypatch.setattr(
        router_module.services,
        "build_swot_response",
        reject_selection,
    )

    response = client.post(
        "/api/livelihood/assess/beneficiary-1",
        json={"livelihood": "OTHER"},
    )

    assert response.status_code == 422
    assert "TRADE" in response.json()["detail"]
    assert "LIVESTOCK & ANIMAL HUSBANDRY" in response.json()["detail"]
    assert "AGRICULTURE & PLANTATION CROPS" in response.json()["detail"]
    assert database.last_insert is None


def test_assess_missing_beneficiary_returns_404(monkeypatch):
    database = FakeSupabase({"beneficiaries": []})
    monkeypatch.setattr(router_module, "get_supabase", lambda: database)

    response = client.post("/api/livelihood/assess/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Beneficiary not found."}
    assert database.last_insert is None


def test_assess_insert_failure_returns_clean_503(monkeypatch):
    database = InsertFailureSupabase(
        {
            "beneficiaries": [
                {
                    "id": "beneficiary-1",
                    "full_name": "Private Name",
                    "district": "Badulla",
                    "ds_division": None,
                    "age": 36,
                    "gender": "Female",
                    "female_headed": True,
                    "disability": False,
                    "aswesuma_category": "Poor",
                    "is_demo": True,
                }
            ]
        }
    )
    monkeypatch.setattr(router_module, "get_supabase", lambda: database)
    monkeypatch.setattr(
        router_module.services,
        "build_swot_response",
        lambda features: _swot_response(),
    )

    response = client.post("/api/livelihood/assess/beneficiary-1")

    assert response.status_code == 503
    assert response.json() == {
        "detail": router_module.DATABASE_UNAVAILABLE_MESSAGE
    }
    assert "raw insert" not in response.text


def test_assess_uses_original_fact_when_gemini_fails(monkeypatch):
    database = FakeSupabase(
        {
            "beneficiaries": [
                {
                    "id": "beneficiary-1",
                    "full_name": "Private Name",
                    "district": "Badulla",
                    "ds_division": None,
                    "age": 36,
                    "gender": "Female",
                    "female_headed": True,
                    "disability": False,
                    "aswesuma_category": "Poor",
                    "is_demo": True,
                }
            ]
        }
    )
    source = "Observed demand was 61% in the district."
    monkeypatch.setattr(router_module, "get_supabase", lambda: database)
    monkeypatch.setattr(
        router_module.services,
        "recommend_with_context",
        lambda features: {
            "recommendations": _swot_response()["recommendations"],
            "confidence": "normal",
            "notes": [],
            "decision_trail": {
                "version": 1,
                "recommendation": RECOMMENDATION_TRAIL,
            },
        },
    )
    monkeypatch.setattr(
        model_2_swot,
        "get_livelihood_factors",
        lambda livelihood, district: [
            {
                "category": "strengths",
                "text": source,
                "source": "Survey",
                "district": district,
                "is_estimated": False,
                "scope": "livelihood",
            }
        ],
    )
    monkeypatch.setattr(
        model_2_swot,
        "get_viability",
        lambda livelihood, district: {
            **VIABILITY,
            "confidence": 0.8,
        },
    )
    monkeypatch.setattr(
        model_2_writer,
        "_generate_rewrites",
        lambda statements: (_ for _ in ()).throw(ConnectionError("offline")),
    )
    monkeypatch.setattr(
        router_module.services,
        "get_viability_previews",
        lambda livelihoods, district: [None for _ in livelihoods],
    )

    response = client.post("/api/livelihood/assess/beneficiary-1")

    assert response.status_code == 200
    saved_strength = response.json()["swot"]["strengths"][0]
    assert saved_strength["text"] == source
    assert saved_strength["evidence"] == source
    assert database.last_insert["status"] == "draft"
    wording_step = next(
        step
        for step in response.json()["decision_trail"]["swot"]["steps"]
        if step["id"] == "swot-wording"
    )
    assert wording_step["details"]["original_count"] == 1
    assert wording_step["details"]["points"][0]["wording"] == "original"
    assert wording_step["summary"] == (
        "1 sentence was checked against its source fact. "
        "0 sentences were reworded; 1 sentence kept the original wording."
    )
    facts_step = next(
        step
        for step in response.json()["decision_trail"]["swot"]["steps"]
        if step["id"] == "swot-facts"
    )
    assert facts_step["summary"] == "1 of 1 fact is from this district."
    confidence_step = next(
        step
        for step in response.json()["decision_trail"]["swot"]["steps"]
        if step["id"] == "swot-confidence"
    )
    assert "supporting record count" not in confidence_step["summary"]


def test_assessment_history_is_newest_first(monkeypatch):
    database = FakeSupabase(
        {
            "livelihood_assessments": [
                _assessment_record("older", "2026-10-20T10:00:00Z"),
                _assessment_record("newer", "2026-10-21T10:00:00Z"),
            ]
        }
    )
    monkeypatch.setattr(router_module, "get_supabase", lambda: database)

    response = client.get(
        "/api/livelihood/assessments/beneficiary-1"
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["newer", "older"]
    assert all(item["decision_trail"] is None for item in response.json())


def test_plan_endpoint(monkeypatch):
    monkeypatch.setattr(
        "app.components.livelihood_planning.services.build_swot",
        lambda livelihood, features: EMPTY_SWOT,
    )
    response = client.post("/api/livelihood/plan", json={})

    assert response.status_code == 200
    assert response.json()["plan"]["placeholder"] is True
    assert response.json()["plan"]["validation"] == {"ok": True, "issues": []}
    assert response.json()["placeholder"] is True
    assert "decision_trail" not in response.json()
