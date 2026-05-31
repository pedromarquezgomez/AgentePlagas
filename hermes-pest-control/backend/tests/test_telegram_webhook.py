from fastapi.testclient import TestClient

from app.adapters.telegram_adapter import TelegramAdapter
from app.dependencies import admin_auth
from app.main import app
from app.routes import telegram as telegram_route
from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage
from app.schemas.outgoing_message import OutgoingMessage


client = TestClient(app)


class SpyTelegramAdapter(TelegramAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.sent_messages: list[OutgoingMessage] = []

    async def send_message(self, outgoing_message: OutgoingMessage) -> dict:
        self.sent_messages.append(outgoing_message)
        return {"ok": True, "result": {"message_id": 999}}


class SpyConversationService:
    def __init__(self) -> None:
        self.received_messages: list[IncomingMessage] = []

    def build_conversation_id(self, message: IncomingMessage) -> str:
        return f"{message.channel}:{message.external_user_id}"

    async def handle_incoming_message(self, message: IncomingMessage) -> AgentResponse:
        self.received_messages.append(message)
        return AgentResponse(
            reply="Respuesta de prueba",
            action={"type": "collect_missing_data", "missing_fields": ["location"]},
            incident={"should_create": False},
        )


def _telegram_text_payload() -> dict:
    return {
        "update_id": 1000,
        "message": {
            "message_id": 55,
            "from": {
                "id": 12345,
                "is_bot": False,
                "first_name": "Pedro",
                "username": "pedro_test",
            },
            "chat": {"id": 67890, "type": "private"},
            "date": 1710000000,
            "text": "Tengo cucarachas en la cocina en Torremolinos",
        },
    }


def test_telegram_webhook_processes_update_and_returns_ok(monkeypatch) -> None:
    adapter = SpyTelegramAdapter()
    conversation_service = SpyConversationService()
    monkeypatch.setattr(telegram_route, "telegram_adapter", adapter)
    monkeypatch.setattr(telegram_route, "conversation_service", conversation_service)
    monkeypatch.setattr(telegram_route.settings, "telegram_webhook_secret", "")

    response = client.post("/webhooks/telegram", json=_telegram_text_payload())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert len(conversation_service.received_messages) == 1
    assert conversation_service.received_messages[0].external_user_id == "12345"
    assert conversation_service.received_messages[0].external_chat_id == "67890"
    assert conversation_service.received_messages[0].metadata["username"] == "pedro_test"
    assert len(adapter.sent_messages) == 1
    assert adapter.sent_messages[0].external_chat_id == "67890"
    assert adapter.sent_messages[0].text == "Respuesta de prueba"


def test_telegram_webhook_requires_secret_when_configured(monkeypatch) -> None:
    adapter = SpyTelegramAdapter()
    conversation_service = SpyConversationService()
    monkeypatch.setattr(telegram_route, "telegram_adapter", adapter)
    monkeypatch.setattr(telegram_route, "conversation_service", conversation_service)
    monkeypatch.setattr(telegram_route.settings, "telegram_webhook_secret", "secret")

    missing_secret_response = client.post("/webhooks/telegram", json=_telegram_text_payload())
    valid_secret_response = client.post(
        "/webhooks/telegram",
        json=_telegram_text_payload(),
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )

    assert missing_secret_response.status_code == 401
    assert valid_secret_response.status_code == 200


def test_telegram_webhook_is_not_blocked_by_admin_auth(monkeypatch) -> None:
    adapter = SpyTelegramAdapter()
    conversation_service = SpyConversationService()
    monkeypatch.setattr(telegram_route, "telegram_adapter", adapter)
    monkeypatch.setattr(telegram_route, "conversation_service", conversation_service)
    monkeypatch.setattr(telegram_route.settings, "telegram_webhook_secret", "")
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.post("/webhooks/telegram", json=_telegram_text_payload())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
