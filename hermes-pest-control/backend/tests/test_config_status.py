from fastapi.testclient import TestClient

from app.main import app
from app.routes import config_status as config_status_route


client = TestClient(app)


def test_config_status_returns_safe_configuration(monkeypatch) -> None:
    monkeypatch.setattr(config_status_route.settings, "app_env", "development")
    monkeypatch.setattr(config_status_route.settings, "hermes_mode", "mock")
    monkeypatch.setattr(config_status_route.settings, "telegram_bot_token", "secret-token")
    monkeypatch.setattr(config_status_route.settings, "firebase_project_id", "")
    monkeypatch.setattr(config_status_route.settings, "firebase_credentials_path", "")
    monkeypatch.setattr(config_status_route.settings, "firebase_credentials_json", "secret-json")
    monkeypatch.setattr(config_status_route.settings, "use_firestore_emulator", False)
    monkeypatch.setattr(config_status_route.settings, "hermes_api_key", "secret-api-key")

    response = client.get("/config/status")

    body = response.json()
    assert response.status_code == 200
    assert body == {
        "app_env": "development",
        "hermes_mode": "mock",
        "telegram_configured": True,
        "firestore_mode": "real",
        "firebase_project_id_configured": False,
    }
    assert "telegram_bot_token" not in body
    assert "hermes_api_key" not in body
    assert "firebase_credentials_json" not in body


def test_config_status_reports_mock_firestore_in_test(monkeypatch) -> None:
    monkeypatch.setattr(config_status_route.settings, "app_env", "test")
    monkeypatch.setattr(config_status_route.settings, "firebase_credentials_path", "secret-path")
    monkeypatch.setattr(config_status_route.settings, "firebase_credentials_json", "secret-json")
    monkeypatch.setattr(config_status_route.settings, "use_firestore_emulator", True)

    response = client.get("/config/status")

    assert response.status_code == 200
    assert response.json()["firestore_mode"] == "mock"
