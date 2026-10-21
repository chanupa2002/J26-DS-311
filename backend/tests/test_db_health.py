from fastapi.testclient import TestClient

import app.main as main_module

client = TestClient(main_module.app)


class FakeStorage:
    def list_buckets(self):
        return []


class FakeSupabase:
    storage = FakeStorage()


def test_database_health_ok(monkeypatch):
    monkeypatch.setattr(main_module, "get_supabase", lambda: FakeSupabase())

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


def test_database_health_not_configured(monkeypatch):
    def raise_missing_credentials():
        raise RuntimeError("Missing test credentials")

    monkeypatch.setattr(main_module, "get_supabase", raise_missing_credentials)

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"database": "not_configured"}
