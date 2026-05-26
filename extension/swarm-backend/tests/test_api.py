"""Basic API health and route tests."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_models_list():
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
