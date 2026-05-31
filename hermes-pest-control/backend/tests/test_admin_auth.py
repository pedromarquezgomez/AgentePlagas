from fastapi.testclient import TestClient

from app.dependencies import admin_auth
from app.main import app
from app.routes import audit as audit_route
from app.routes import incidents as incidents_route
from app.services.decision_audit_service import DecisionAuditService
from app.services.incident_service import IncidentService
from app.services.mock_firestore_service import MockFirestoreService


client = TestClient(app)


def test_protected_endpoint_allows_access_when_admin_auth_disabled(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "api_key")
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", False)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "")

    response = client.get("/incidents")

    assert response.status_code == 200


def test_protected_endpoint_requires_header_when_admin_auth_enabled(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "api_key")
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/incidents")

    assert response.status_code == 401
    assert "test-admin-key" not in response.text


def test_protected_endpoint_rejects_wrong_admin_api_key(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "api_key")
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/incidents",
        headers={"X-Admin-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert "test-admin-key" not in response.text
    assert "wrong-key" not in response.text


def test_protected_endpoint_accepts_correct_admin_api_key(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "api_key")
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/incidents",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200


def test_health_remains_public_when_admin_auth_enabled(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "api_key")
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_audit_endpoint_is_protected_when_admin_auth_enabled(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "api_key")
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/audit/decisions")

    assert response.status_code == 401


def test_audit_endpoint_accepts_correct_admin_api_key(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = DecisionAuditService(firestore_service)
    monkeypatch.setattr(audit_route, "decision_audit_service", service)
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "api_key")
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/audit/decisions",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200


def test_firebase_auth_accepts_verified_bearer_token(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "firebase")
    monkeypatch.setattr(admin_auth.settings, "firebase_auth_enabled", True)

    def fake_verify(token: str, current_settings=admin_auth.settings) -> dict:
        assert token == "valid-token"
        return {"uid": "firebase-user-1", "email": "admin@example.com", "name": "Admin"}

    monkeypatch.setattr(admin_auth, "verify_firebase_id_token", fake_verify)

    response = client.get(
        "/incidents",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200


def test_firebase_auth_rejects_missing_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "firebase")
    monkeypatch.setattr(admin_auth.settings, "firebase_auth_enabled", True)

    response = client.get("/incidents")

    assert response.status_code == 401
    assert "Bearer" not in response.text


def test_firebase_auth_rejects_invalid_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "firebase")
    monkeypatch.setattr(admin_auth.settings, "firebase_auth_enabled", True)

    def fake_verify(token: str, current_settings=admin_auth.settings) -> dict:
        raise admin_auth.FirebaseAuthError("invalid")

    monkeypatch.setattr(admin_auth, "verify_firebase_id_token", fake_verify)

    response = client.get(
        "/incidents",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert "invalid-token" not in response.text


def test_auth_mode_disabled_allows_development_access(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "disabled")
    monkeypatch.setattr(admin_auth.settings, "app_env", "development")

    response = client.get("/incidents")

    assert response.status_code == 200


def test_auth_mode_disabled_is_rejected_in_production(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "disabled")
    monkeypatch.setattr(admin_auth.settings, "app_env", "production")

    response = client.get("/incidents")

    assert response.status_code == 500


def test_api_key_mode_requires_key_in_production_even_if_legacy_flag_disabled(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "auth_mode", "api_key")
    monkeypatch.setattr(admin_auth.settings, "app_env", "production")
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", False)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    missing_key_response = client.get("/incidents")
    valid_key_response = client.get(
        "/incidents",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert missing_key_response.status_code == 401
    assert valid_key_response.status_code == 200


def test_webhooks_remain_public_in_firebase_auth_mode(monkeypatch) -> None:
    from app.routes import telegram as telegram_route
    from app.schemas.agent_response import AgentResponse

    class SpyTelegramAdapter:
        def parse_incoming(self, raw_update: dict) -> object:
            from app.schemas.incoming_message import IncomingMessage

            return IncomingMessage(
                channel="telegram",
                external_user_id="123",
                external_chat_id="456",
                message_type="text",
                text="Hola",
                attachments=[],
                metadata={},
            )

        async def send_message(self, outgoing_message: object) -> dict:
            return {"ok": True}

    class SpyConversationService:
        def build_conversation_id(self, message: object) -> str:
            return "telegram:123"

        async def handle_incoming_message(self, message: object) -> AgentResponse:
            return AgentResponse(
                reply="Hola",
                action={"type": "collect_missing_data", "missing_fields": ["pest_type"]},
                incident={"should_create": False},
            )

    monkeypatch.setattr(admin_auth.settings, "auth_mode", "firebase")
    monkeypatch.setattr(telegram_route.settings, "telegram_webhook_secret", "")
    monkeypatch.setattr(telegram_route, "telegram_adapter", SpyTelegramAdapter())
    monkeypatch.setattr(telegram_route, "conversation_service", SpyConversationService())

    response = client.post("/webhooks/telegram", json={"message": {"text": "Hola"}})

    assert response.status_code == 200
