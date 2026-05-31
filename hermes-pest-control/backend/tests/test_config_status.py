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
    monkeypatch.setattr(config_status_route.settings, "hermes_api_url", "https://secret-hermes.test/agent")
    monkeypatch.setattr(config_status_route.settings, "hermes_agent_mode", "local")
    monkeypatch.setattr(config_status_route.settings, "hermes_skills_dir", "../hermes/skills")
    monkeypatch.setattr(config_status_route.settings, "admin_api_key", "secret-admin-key")
    monkeypatch.setattr(config_status_route.settings, "require_admin_auth", True)
    monkeypatch.setattr(config_status_route.settings, "google_calendar_enabled", True)
    monkeypatch.setattr(config_status_route.settings, "google_calendar_id", "secret-calendar-id")
    monkeypatch.setattr(
        config_status_route.settings,
        "google_calendar_credentials_json",
        "secret-google-json",
    )

    response = client.get("/config/status")

    body = response.json()
    assert response.status_code == 200
    assert body == {
        "app_env": "development",
        "hermes_mode": "mock",
        "hermes_api_url_configured": True,
        "hermes_api_key_configured": True,
        "hermes_agent_mode": "local",
        "hermes_skills_dir_configured": True,
        "telegram_configured": True,
        "firestore_mode": "real",
        "firebase_project_id_configured": False,
        "firebase_credentials_configured": True,
        "firestore_emulator_enabled": False,
        "admin_auth_required": True,
        "admin_api_key_configured": True,
        "google_calendar_enabled": True,
        "google_calendar_id_configured": True,
        "google_calendar_credentials_configured": True,
    }
    assert "telegram_bot_token" not in body
    assert "hermes_api_key" not in body
    assert "hermes_api_url" not in body
    assert "secret-hermes" not in response.text
    assert "admin_api_key" not in body
    assert "secret-admin-key" not in response.text
    assert "firebase_credentials_json" not in body
    assert "secret-json" not in response.text
    assert "secret-calendar-id" not in response.text
    assert "secret-google-json" not in response.text


def test_config_status_reports_mock_firestore_in_test(monkeypatch) -> None:
    monkeypatch.setattr(config_status_route.settings, "app_env", "test")
    monkeypatch.setattr(config_status_route.settings, "firebase_credentials_path", "secret-path")
    monkeypatch.setattr(config_status_route.settings, "firebase_credentials_json", "secret-json")
    monkeypatch.setattr(config_status_route.settings, "use_firestore_emulator", True)

    response = client.get("/config/status")

    assert response.status_code == 200
    assert response.json()["firestore_mode"] == "mock"
    assert response.json()["firebase_credentials_configured"] is True
    assert response.json()["firestore_emulator_enabled"] is True
