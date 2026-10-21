"""API tests for the livelihood-planning endpoints."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.components.livelihood_planning import router as router_module
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


def _swot_response():
    return {
        "recommendations": [
            {"livelihood": "TRADE", "score": 0.7, "reasons": []}
        ],
        "swot": EMPTY_SWOT,
        "viability": VIABILITY,
        "confidence": "normal",
        "notes": ["Model note"],
        "placeholder": False,
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

    def select(self, columns):
        self.selected = columns
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
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


def test_recommend_endpoint():
    response = client.post("/api/livelihood/recommend", json={})

    assert response.status_code == 200
    assert len(response.json()["recommendations"]) == 3
    assert response.json()["placeholder"] is False


def test_recommend_keeps_old_keys_and_adds_explanation_fields():
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
    monkeypatch.setattr(
        router_module.services,
        "recommend_with_context",
        lambda features: {
            "recommendations": _swot_response()["recommendations"],
            "confidence": "normal",
            "notes": ["Shared note", "Model 1 note"],
        },
    )
    monkeypatch.setattr(
        router_module.services,
        "build_swot_report",
        lambda livelihood, features: {
            "swot": EMPTY_SWOT,
            "viability": VIABILITY,
            "confidence": "low",
            "notes": ["Shared note", "Model 2 note"],
        },
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
    }


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
    assert database.last_insert["status"] == "draft"
    assert response.json()["status"] == "draft"


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

    response = client.post("/api/livelihood/assess/beneficiary-1")

    assert response.status_code == 200
    saved_strength = response.json()["swot"]["strengths"][0]
    assert saved_strength["text"] == source
    assert saved_strength["evidence"] == source
    assert database.last_insert["status"] == "draft"


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
