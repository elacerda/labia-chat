"""Testes do endpoint de health check."""

from fastapi.testclient import TestClient

from labia_chat.main import app

client = TestClient(app)


def test_health_check_returns_200() -> None:
    """Testa se o endpoint /health retorna status 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_returns_correct_payload() -> None:
    """Testa se o endpoint /health retorna o payload esperado."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "labia-chat"
