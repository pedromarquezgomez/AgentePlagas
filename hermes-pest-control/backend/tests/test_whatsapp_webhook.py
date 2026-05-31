from fastapi.testclient import TestClient

from app.adapters.whatsapp_adapter import WhatsAppAdapter
from app.main import app
from app.routes import whatsapp as whatsapp_route
from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage
from app.schemas.outgoing_message import OutgoingMessage
from app.services.conversation_service import ConversationService
from app.services.mock_firestore_service import MockFirestoreService

client = TestClient(app)


class SpyWhatsAppAdapter(WhatsAppAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.sent_messages: list[OutgoingMessage] = []

    async def send_message(self, outgoing_message: OutgoingMessage) -> dict:
        self.sent_messages.append(outgoing_message)
        return {"messages": [{"id": "wamid.sent"}]}


class SpyConversationService:
    def __init__(self) -> None:
        self.received_messages: list[IncomingMessage] = []

    def build_conversation_id(self, message: IncomingMessage) -> str:
        return f"{message.channel}:{message.external_user_id}"

    async def handle_incoming_message(self, message: IncomingMessage) -> AgentResponse:
        self.received_messages.append(message)
        return AgentResponse(
            reply="Respuesta WhatsApp",
            action={"type": "collect_missing_data", "missing_fields": ["location"]},
            incident={"should_create": False},
        )


def whatsapp_text_payload(text: str = "Tengo cucarachas en la cocina en Torremolinos") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-1",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "34999000111",
                                "phone_number_id": "phone-number-id",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Pedro"},
                                    "wa_id": "34600000000",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "34600000000",
                                    "id": "wamid.123",
                                    "timestamp": "1710000000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def test_whatsapp_webhook_disabled_returns_controlled_status(monkeypatch) -> None:
    monkeypatch.setattr(whatsapp_route.settings, "whatsapp_enabled", False)

    response = client.post("/webhooks/whatsapp", json=whatsapp_text_payload())

    assert response.status_code == 200
    assert response.json() == {"status": "disabled"}


def test_whatsapp_webhook_processes_update_with_mocks(monkeypatch) -> None:
    adapter = SpyWhatsAppAdapter()
    conversation_service = SpyConversationService()
    monkeypatch.setattr(whatsapp_route.settings, "whatsapp_enabled", True)
    monkeypatch.setattr(whatsapp_route.settings, "whatsapp_webhook_secret", "")
    monkeypatch.setattr(whatsapp_route, "whatsapp_adapter", adapter)
    monkeypatch.setattr(whatsapp_route, "conversation_service", conversation_service)

    response = client.post("/webhooks/whatsapp", json=whatsapp_text_payload())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert len(conversation_service.received_messages) == 1
    assert conversation_service.received_messages[0].channel == "whatsapp"
    assert conversation_service.received_messages[0].external_user_id == "34600000000"
    assert len(adapter.sent_messages) == 1
    assert adapter.sent_messages[0].channel == "whatsapp"
    assert adapter.sent_messages[0].external_chat_id == "34600000000"


def test_whatsapp_webhook_requires_secret_when_configured(monkeypatch) -> None:
    adapter = SpyWhatsAppAdapter()
    conversation_service = SpyConversationService()
    monkeypatch.setattr(whatsapp_route.settings, "whatsapp_enabled", True)
    monkeypatch.setattr(whatsapp_route.settings, "whatsapp_webhook_secret", "secret")
    monkeypatch.setattr(whatsapp_route, "whatsapp_adapter", adapter)
    monkeypatch.setattr(whatsapp_route, "conversation_service", conversation_service)

    missing_secret_response = client.post("/webhooks/whatsapp", json=whatsapp_text_payload())
    valid_secret_response = client.post(
        "/webhooks/whatsapp",
        json=whatsapp_text_payload(),
        headers={"X-Whatsapp-Webhook-Secret": "secret"},
    )

    assert missing_secret_response.status_code == 401
    assert valid_secret_response.status_code == 200


def test_whatsapp_verify_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(whatsapp_route.settings, "whatsapp_verify_token", "verify")

    response = client.get(
        "/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=verify&hub.challenge=abc123"
    )

    assert response.status_code == 200
    assert response.text == "abc123"


def test_whatsapp_real_conversation_creates_incident_and_audit(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    adapter = SpyWhatsAppAdapter()
    conversation_service = ConversationService(firestore_service=firestore_service)
    monkeypatch.setattr(whatsapp_route.settings, "whatsapp_enabled", True)
    monkeypatch.setattr(whatsapp_route.settings, "whatsapp_webhook_secret", "")
    monkeypatch.setattr(whatsapp_route, "whatsapp_adapter", adapter)
    monkeypatch.setattr(whatsapp_route, "conversation_service", conversation_service)

    response = client.post(
        "/webhooks/whatsapp",
        json=whatsapp_text_payload(
            "Tengo cucarachas en la cocina en Torremolinos desde hace una semana"
        ),
    )

    assert response.status_code == 200
    assert adapter.sent_messages

    import anyio

    decision_records = anyio.run(
        firestore_service.list_documents,
        "decision_records",
        {"conversation_id": "whatsapp:34600000000"},
    )
    persisted_incidents = anyio.run(
        firestore_service.list_documents,
        "incidents",
        {"conversation_id": "whatsapp:34600000000"},
    )
    assert len(persisted_incidents) == 1
    assert persisted_incidents[0]["channel"] == "whatsapp"
    assert len(decision_records) == 1
    assert decision_records[0]["channel"] == "whatsapp"


def test_whatsapp_human_review_matches_other_channels(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    adapter = SpyWhatsAppAdapter()
    conversation_service = ConversationService(firestore_service=firestore_service)
    monkeypatch.setattr(whatsapp_route.settings, "whatsapp_enabled", True)
    monkeypatch.setattr(whatsapp_route.settings, "whatsapp_webhook_secret", "")
    monkeypatch.setattr(whatsapp_route, "whatsapp_adapter", adapter)
    monkeypatch.setattr(whatsapp_route, "conversation_service", conversation_service)

    response = client.post(
        "/webhooks/whatsapp",
        json=whatsapp_text_payload("Me he intoxicado con un producto y necesito ayuda"),
    )

    import anyio

    review_items = anyio.run(
        firestore_service.list_documents,
        "human_review_items",
        {"conversation_id": "whatsapp:34600000000"},
    )
    assert response.status_code == 200
    assert len(review_items) == 1
    assert review_items[0]["channel"] == "whatsapp"
