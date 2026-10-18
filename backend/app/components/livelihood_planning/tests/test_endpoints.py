"""API tests for the livelihood-planning endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.components.livelihood_planning.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


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


def test_swot_endpoint():
    response = client.post("/api/livelihood/swot", json={})

    assert response.status_code == 200
    assert set(response.json()["swot"]) == {
        "strengths",
        "weaknesses",
        "opportunities",
        "threats",
    }
    assert response.json()["placeholder"] is True


def test_plan_endpoint():
    response = client.post("/api/livelihood/plan", json={})

    assert response.status_code == 200
    assert response.json()["plan"]["placeholder"] is True
    assert response.json()["plan"]["validation"] == {"ok": True, "issues": []}
    assert response.json()["placeholder"] is True
