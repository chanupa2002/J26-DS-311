"""API tests for the livelihood-planning placeholder endpoints."""

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
    assert response.json()["placeholder"] is True


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
