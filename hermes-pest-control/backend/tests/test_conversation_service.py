import pytest

from app.schemas.incoming_message import IncomingMessage
from app.services.conversation_service import ConversationService
from app.services.mock_firestore_service import MockFirestoreService


def test_conversation_service_builds_internal_conversation_id() -> None:
    service = ConversationService()
    message = IncomingMessage(
        channel="telegram",
        external_user_id="12345",
        external_chat_id="67890",
        message_type="text",
        text="Tengo cucarachas",
    )

    assert service.build_conversation_id(message) == "telegram:12345"


class InvalidHermesService:
    async def process_message(self, message: IncomingMessage, conversation_id: str) -> dict:
        return {"reply": "invalid", "action": {"type": "unknown_action"}}


@pytest.mark.asyncio
async def test_conversation_service_returns_safe_response_for_invalid_hermes() -> None:
    firestore_service = MockFirestoreService()
    service = ConversationService(
        hermes_service=InvalidHermesService(),
        firestore_service=firestore_service,
    )
    message = IncomingMessage(
        channel="telegram",
        external_user_id="12345",
        external_chat_id="67890",
        message_type="text",
        text="Tengo cucarachas",
    )

    response = await service.handle_incoming_message(message)

    assert response.action.type == "escalate_to_human"
    assert response.incident is not None
    assert response.incident.should_create is True
    assert response.incident.status == "pending_review"
    decision_records = await firestore_service.list_documents(
        "decision_records",
        filters={"conversation_id": "telegram:12345"},
    )
    assert len(decision_records) == 1
    assert decision_records[0]["fallback_used"] is True
    assert (
        decision_records[0]["fallback_reason"]
        == "conversation_service_invalid_agent_response"
    )


@pytest.mark.asyncio
async def test_conversation_service_persists_conversation_messages_and_incident() -> None:
    firestore_service = MockFirestoreService()
    service = ConversationService(firestore_service=firestore_service)
    message = IncomingMessage(
        channel="telegram",
        external_user_id="test-user-1",
        external_chat_id="test-chat-1",
        message_type="text",
        text="Tengo cucarachas en la cocina en Torremolinos desde hace una semana",
    )

    response = await service.handle_incoming_message(message)

    conversation = await firestore_service.get_document(
        "conversations",
        "telegram:test-user-1",
    )
    messages = await firestore_service.list_documents(
        "messages",
        filters={"conversation_id": "telegram:test-user-1"},
    )
    incidents = await firestore_service.list_documents(
        "incidents",
        filters={"conversation_id": "telegram:test-user-1"},
    )
    decision_records = await firestore_service.list_documents(
        "decision_records",
        filters={"conversation_id": "telegram:test-user-1"},
    )

    assert response.action.type == "create_incident"
    assert conversation is not None
    assert conversation["status"] == "active"
    assert len(messages) == 2
    assert {message["direction"] for message in messages} == {"inbound", "outbound"}
    assert len(incidents) == 1
    assert incidents[0]["status"] == "pending_review"
    assert len(decision_records) == 1
    assert decision_records[0]["trace_id"]
    assert decision_records[0]["message_id"]
    assert decision_records[0]["incident_id"] == incidents[0]["id"]
    assert decision_records[0]["hermes_mode"] == "mock"
    assert decision_records[0]["action_type"] == "create_incident"
    assert decision_records[0]["fallback_used"] is False
    assert decision_records[0]["response_contract_version"] == "AgentResponse.v1"
