from fastapi.testclient import TestClient

from app.main import app
from app.routes import config_status as config_status_route


client = TestClient(app)


def test_config_status_returns_safe_configuration(monkeypatch) -> None:
    monkeypatch.setattr(config_status_route.settings, "app_env", "development")
    monkeypatch.setattr(config_status_route.settings, "cors_allowed_origins", "https://panel.example.com")
    monkeypatch.setattr(config_status_route.settings, "frontend_public_url", "https://panel.example.com")
    monkeypatch.setattr(config_status_route.settings, "agent_provider", "llm")
    monkeypatch.setattr(config_status_route.settings, "hermes_mode", "mock")
    monkeypatch.setattr(config_status_route.settings, "telegram_bot_token", "secret-token")
    monkeypatch.setattr(config_status_route.settings, "firebase_project_id", "")
    monkeypatch.setattr(config_status_route.settings, "firebase_credentials_path", "")
    monkeypatch.setattr(config_status_route.settings, "firebase_credentials_json", "secret-json")
    monkeypatch.setattr(config_status_route.settings, "use_firestore_emulator", False)
    monkeypatch.setattr(config_status_route.settings, "hermes_api_key", "secret-api-key")
    monkeypatch.setattr(config_status_route.settings, "hermes_api_url", "https://secret-hermes.test/agent")
    monkeypatch.setattr(config_status_route.settings, "hermes_shadow_mode", True)
    monkeypatch.setattr(
        config_status_route.settings,
        "hermes_shadow_api_url",
        "https://secret-shadow.test/agent",
    )
    monkeypatch.setattr(config_status_route.settings, "hermes_shadow_api_key", "secret-shadow-key")
    monkeypatch.setattr(config_status_route.settings, "hermes_shadow_sample_rate", 0.5)
    monkeypatch.setattr(config_status_route.settings, "hermes_pilot_mode", False)
    monkeypatch.setattr(config_status_route.settings, "hermes_pilot_allowed_channels", "telegram")
    monkeypatch.setattr(config_status_route.settings, "hermes_pilot_sample_rate", 1.0)
    monkeypatch.setattr(config_status_route.settings, "hermes_pilot_require_gate", True)
    monkeypatch.setattr(config_status_route.settings, "hermes_agent_mode", "local")
    monkeypatch.setattr(config_status_route.settings, "hermes_agent_api_key", "secret-agent-key")
    monkeypatch.setattr(config_status_route.settings, "hermes_skills_dir", "../hermes/skills")
    monkeypatch.setattr(config_status_route.settings, "llm_provider", "openai")
    monkeypatch.setattr(config_status_route.settings, "llm_api_key", "")
    monkeypatch.setattr(config_status_route.settings, "llm_model", "")
    monkeypatch.setattr(config_status_route.settings, "llm_fallback_provider", "mock")
    monkeypatch.setattr(config_status_route.settings, "llm_active_mode", "pilot")
    monkeypatch.setattr(config_status_route.settings, "openai_api_key", "secret-openai-key")
    monkeypatch.setattr(config_status_route.settings, "openai_model", "secret-model")
    monkeypatch.setattr(config_status_route.settings, "agent_max_output_tokens", 1200)
    monkeypatch.setattr(config_status_route.settings, "admin_api_key", "secret-admin-key")
    monkeypatch.setattr(config_status_route.settings, "require_admin_auth", True)
    monkeypatch.setattr(config_status_route.settings, "auth_mode", "firebase")
    monkeypatch.setattr(config_status_route.settings, "firebase_auth_enabled", True)
    monkeypatch.setattr(config_status_route.settings, "google_calendar_enabled", True)
    monkeypatch.setattr(config_status_route.settings, "google_calendar_id", "secret-calendar-id")
    monkeypatch.setattr(
        config_status_route.settings,
        "google_calendar_credentials_json",
        "secret-google-json",
    )
    monkeypatch.setattr(config_status_route.settings, "whatsapp_enabled", True)
    monkeypatch.setattr(config_status_route.settings, "whatsapp_provider", "meta")
    monkeypatch.setattr(config_status_route.settings, "whatsapp_access_token", "secret-whatsapp-token")
    monkeypatch.setattr(config_status_route.settings, "whatsapp_phone_number_id", "secret-phone-id")
    monkeypatch.setattr(config_status_route.settings, "whatsapp_verify_token", "secret-verify-token")

    response = client.get("/config/status")

    body = response.json()
    assert response.status_code == 200
    assert body == {
        "app_env": "development",
        "cors_allowed_origins_configured": True,
        "frontend_public_url_configured": True,
        "agent_provider": "llm",
        "hermes_mode": "mock",
        "hermes_api_url_configured": True,
        "hermes_api_key_configured": True,
        "hermes_shadow_mode": True,
        "hermes_shadow_api_url_configured": True,
        "hermes_shadow_api_key_configured": True,
        "hermes_shadow_sample_rate": "0.5",
        "hermes_pilot_mode": False,
        "hermes_pilot_allowed_channels": "telegram",
        "hermes_pilot_sample_rate": "1.0",
        "hermes_pilot_require_gate": True,
        "hermes_agent_mode": "local",
        "hermes_agent_api_key_configured": True,
        "hermes_skills_dir_configured": True,
        "llm_provider": "openai",
        "llm_active_mode": "pilot",
        "llm_api_key_configured": True,
        "llm_model_configured": True,
        "llm_fallback_provider": "mock",
        "openai_api_key_configured": True,
        "openai_model_configured": True,
        "agent_max_output_tokens_configured": True,
        "telegram_configured": True,
        "firestore_mode": "real",
        "firebase_project_id_configured": False,
        "firebase_credentials_configured": True,
        "firestore_emulator_enabled": False,
        "auth_mode": "firebase",
        "firebase_auth_enabled": True,
        "admin_auth_required": True,
        "admin_api_key_configured": True,
        "google_calendar_enabled": True,
        "google_calendar_id_configured": True,
        "google_calendar_credentials_configured": True,
        "whatsapp_enabled": True,
        "whatsapp_provider": "meta",
        "whatsapp_access_token_configured": True,
        "whatsapp_phone_number_id_configured": True,
        "whatsapp_verify_token_configured": True,
    }
    assert "telegram_bot_token" not in body
    assert "hermes_api_key" not in body
    assert "hermes_api_url" not in body
    assert "secret-hermes" not in response.text
    assert "hermes_shadow_api_url" not in body
    assert "secret-shadow" not in response.text
    assert "hermes_shadow_api_key" not in body
    assert "secret-shadow-key" not in response.text
    assert "hermes_agent_api_key" not in body
    assert "secret-agent-key" not in response.text
    assert "openai_api_key" not in body
    assert "openai_model" not in body
    assert "llm_api_key" not in body
    assert "llm_model" not in body
    assert "secret-openai-key" not in response.text
    assert "secret-model" not in response.text
    assert "admin_api_key" not in body
    assert "secret-admin-key" not in response.text
    assert "firebase_credentials_json" not in body
    assert "secret-json" not in response.text
    assert "secret-calendar-id" not in response.text
    assert "secret-google-json" not in response.text
    assert "secret-whatsapp-token" not in response.text
    assert "secret-phone-id" not in response.text
    assert "secret-verify-token" not in response.text


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
