from fastapi.testclient import TestClient

from app.main import app
from app.routes import health as health_route


client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ready_for_development(monkeypatch) -> None:
    monkeypatch.setattr(health_route.settings, "app_env", "development")
    monkeypatch.setattr(health_route.settings, "auth_mode", "api_key")
    monkeypatch.setattr(health_route.settings, "require_admin_auth", False)
    monkeypatch.setattr(health_route.settings, "firebase_credentials_path", "")
    monkeypatch.setattr(health_route.settings, "firebase_credentials_json", "")
    monkeypatch.setattr(health_route.settings, "firebase_project_id", "")
    monkeypatch.setattr(health_route.settings, "use_firestore_emulator", False)

    response = client.get("/ready")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ready"
    assert body["checks"]["firestore_mode"] == "mock"
    assert body["degraded_reasons"] == []


def test_ready_degraded_when_auth_disabled_in_production(monkeypatch) -> None:
    monkeypatch.setattr(health_route.settings, "app_env", "production")
    monkeypatch.setattr(health_route.settings, "auth_mode", "disabled")
    monkeypatch.setattr(health_route.settings, "firebase_project_id", "project-id")
    monkeypatch.setattr(health_route.settings, "firebase_credentials_path", "")
    monkeypatch.setattr(health_route.settings, "firebase_credentials_json", "")
    monkeypatch.setattr(health_route.settings, "use_firestore_emulator", False)

    response = client.get("/ready")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "degraded"
    assert "AUTH_MODE=disabled" in body["degraded_reasons"][0]


def test_ready_degraded_when_firestore_unconfigured_in_production(monkeypatch) -> None:
    monkeypatch.setattr(health_route.settings, "app_env", "production")
    monkeypatch.setattr(health_route.settings, "auth_mode", "firebase")
    monkeypatch.setattr(health_route.settings, "firebase_auth_enabled", True)
    monkeypatch.setattr(health_route.settings, "firebase_project_id", "")
    monkeypatch.setattr(health_route.settings, "firebase_credentials_path", "")
    monkeypatch.setattr(health_route.settings, "firebase_credentials_json", "")
    monkeypatch.setattr(health_route.settings, "use_firestore_emulator", False)

    response = client.get("/ready")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "degraded"
    assert body["checks"]["firestore_mode"] == "unconfigured"
    assert "Firestore real configuration is required in production." in body["degraded_reasons"]
