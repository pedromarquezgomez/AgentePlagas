import pytest

from app.schemas.incoming_message import IncomingMessage
from app.config.settings import Settings
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


class RealModeHermesService:
    hermes_mode = "real"

    async def process_message(self, *_args, **_kwargs) -> dict:
        return {
            "reply": "Respuesta desde Hermes real de prueba.",
            "action": {"type": "collect_missing_data", "missing_fields": ["location"]},
            "incident": {"should_create": False},
        }


class EscalatingHermesService:
    hermes_mode = "mock"

    async def process_message(self, *_args, **_kwargs) -> dict:
        return {
            "reply": "Gracias por avisarnos. El equipo revisará este caso.",
            "action": {"type": "escalate_to_human", "missing_fields": []},
            "incident": {
                "should_create": True,
                "pest_type": "cucarachas",
                "location": "Torremolinos",
                "affected_area": "cocina",
                "priority": "high",
                "summary": "Caso sensible que requiere revisión humana.",
            },
        }


class UrgentIncidentHermesService:
    hermes_mode = "mock"

    async def process_message(self, *_args, **_kwargs) -> dict:
        return {
            "reply": "Gracias. El equipo revisará el aviso prioritario.",
            "action": {"type": "create_incident", "missing_fields": []},
            "incident": {
                "should_create": True,
                "pest_type": "roedores",
                "location": "Málaga",
                "affected_area": "garaje",
                "priority": "urgent",
                "summary": "Aviso urgente por posible riesgo.",
            },
        }


class FailingShadowHermesService:
    hermes_mode = "real"

    async def process_message(self, *_args, **_kwargs) -> dict:
        raise RuntimeError("shadow unavailable")


class DifferentShadowHermesService:
    hermes_mode = "real"

    async def process_message(self, *_args, **_kwargs) -> dict:
        return {
            "reply": "Para registrar el aviso necesito saber la localidad.",
            "action": {"type": "collect_missing_data", "missing_fields": ["location"]},
            "incident": {"should_create": False},
        }


class FallbackShadowHermesService:
    hermes_mode = "real"

    async def process_message(self, *_args, **_kwargs) -> dict:
        return {
            "reply": "Fallback seguro.",
            "action": {"type": "escalate_to_human", "missing_fields": []},
            "incident": {
                "should_create": True,
                "priority": "medium",
                "summary": "Error procesando respuesta del agente.",
            },
            "metadata": {
                "fallback_used": True,
                "fallback_reason": "HermesClientError:connection_error",
            },
        }


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
    review_items = await firestore_service.list_documents(
        "human_review_items",
        filters={"conversation_id": "telegram:12345"},
    )
    assert len(review_items) == 1
    assert review_items[0]["reason"] == "fallback_used"
    assert review_items[0]["metadata"]["review_reasons"] == [
        "fallback_used",
        "agent_escalation",
    ]


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


@pytest.mark.asyncio
async def test_conversation_service_records_real_hermes_mode() -> None:
    firestore_service = MockFirestoreService()
    service = ConversationService(
        hermes_service=RealModeHermesService(),
        firestore_service=firestore_service,
    )
    message = IncomingMessage(
        channel="telegram",
        external_user_id="real-user",
        external_chat_id="real-chat",
        message_type="text",
        text="Tengo cucarachas",
    )

    response = await service.handle_incoming_message(message)

    decision_records = await firestore_service.list_documents(
        "decision_records",
        filters={"conversation_id": "telegram:real-user"},
    )
    assert response.action.type == "collect_missing_data"
    assert len(decision_records) == 1
    assert decision_records[0]["hermes_mode"] == "real"
    assert decision_records[0]["action_type"] == "collect_missing_data"


@pytest.mark.asyncio
async def test_conversation_service_creates_review_item_for_agent_escalation() -> None:
    firestore_service = MockFirestoreService()
    service = ConversationService(
        hermes_service=EscalatingHermesService(),
        firestore_service=firestore_service,
    )
    message = IncomingMessage(
        channel="telegram",
        external_user_id="escalated-user",
        external_chat_id="escalated-chat",
        message_type="text",
        text="Tengo cucarachas y necesito hablar con una persona",
    )

    response = await service.handle_incoming_message(message)

    review_items = await firestore_service.list_documents(
        "human_review_items",
        filters={"conversation_id": "telegram:escalated-user"},
    )
    decision_records = await firestore_service.list_documents(
        "decision_records",
        filters={"conversation_id": "telegram:escalated-user"},
    )

    assert response.action.type == "escalate_to_human"
    assert len(review_items) == 1
    assert review_items[0]["reason"] == "agent_escalation"
    assert review_items[0]["incident_id"]
    assert review_items[0]["decision_record_id"] == decision_records[0]["id"]


@pytest.mark.asyncio
async def test_conversation_service_creates_review_item_for_urgent_priority() -> None:
    firestore_service = MockFirestoreService()
    service = ConversationService(
        hermes_service=UrgentIncidentHermesService(),
        firestore_service=firestore_service,
    )
    message = IncomingMessage(
        channel="telegram",
        external_user_id="urgent-user",
        external_chat_id="urgent-chat",
        message_type="text",
        text="Hay roedores en el garaje en Málaga",
    )

    response = await service.handle_incoming_message(message)

    review_items = await firestore_service.list_documents(
        "human_review_items",
        filters={"conversation_id": "telegram:urgent-user"},
    )

    assert response.action.type == "create_incident"
    assert response.incident is not None
    assert response.incident.priority == "urgent"
    assert len(review_items) == 1
    assert review_items[0]["reason"] == "urgent_priority"
    assert review_items[0]["priority"] == "urgent"


@pytest.mark.asyncio
async def test_shadow_disabled_does_not_create_shadow_record() -> None:
    firestore_service = MockFirestoreService()
    service = ConversationService(
        firestore_service=firestore_service,
        shadow_hermes_service=FailingShadowHermesService(),
        settings=Settings(hermes_shadow_mode=False),
    )
    message = IncomingMessage(
        channel="telegram",
        external_user_id="shadow-disabled",
        external_chat_id="shadow-disabled-chat",
        message_type="text",
        text="Tengo cucarachas en la cocina en Torremolinos",
    )

    response = await service.handle_incoming_message(message)

    shadow_records = await firestore_service.list_documents("shadow_decision_records")
    assert response.action.type == "create_incident"
    assert shadow_records == []


@pytest.mark.asyncio
async def test_shadow_enabled_without_api_url_does_not_call_shadow() -> None:
    firestore_service = MockFirestoreService()
    service = ConversationService(
        firestore_service=firestore_service,
        settings=Settings(hermes_shadow_mode=True, hermes_shadow_api_url=""),
    )
    message = IncomingMessage(
        channel="telegram",
        external_user_id="shadow-no-url",
        external_chat_id="shadow-no-url-chat",
        message_type="text",
        text="Tengo cucarachas en la cocina en Torremolinos",
    )

    response = await service.handle_incoming_message(message)

    shadow_records = await firestore_service.list_documents("shadow_decision_records")
    assert response.action.type == "create_incident"
    assert shadow_records == []


@pytest.mark.asyncio
async def test_shadow_enabled_creates_shadow_record_with_differences() -> None:
    firestore_service = MockFirestoreService()
    service = ConversationService(
        firestore_service=firestore_service,
        shadow_hermes_service=DifferentShadowHermesService(),
        settings=Settings(hermes_shadow_mode=True, hermes_shadow_sample_rate=1.0),
        random_func=lambda: 0.0,
    )
    message = IncomingMessage(
        channel="telegram",
        external_user_id="shadow-enabled",
        external_chat_id="shadow-enabled-chat",
        message_type="text",
        text="Tengo cucarachas en la cocina en Torremolinos",
    )

    response = await service.handle_incoming_message(message)

    incidents = await firestore_service.list_documents(
        "incidents",
        filters={"conversation_id": "telegram:shadow-enabled"},
    )
    shadow_records = await firestore_service.list_documents(
        "shadow_decision_records",
        filters={"conversation_id": "telegram:shadow-enabled"},
    )
    assert response.action.type == "create_incident"
    assert len(incidents) == 1
    assert len(shadow_records) == 1
    assert shadow_records[0]["primary_action_type"] == "create_incident"
    assert shadow_records[0]["shadow_action_type"] == "collect_missing_data"
    assert shadow_records[0]["primary_should_create"] is True
    assert shadow_records[0]["shadow_should_create"] is False
    assert shadow_records[0]["agreement_summary"] == "differences_detected"
    assert "action_type" in shadow_records[0]["differences"]


@pytest.mark.asyncio
async def test_shadow_error_does_not_break_primary_flow() -> None:
    firestore_service = MockFirestoreService()
    service = ConversationService(
        firestore_service=firestore_service,
        shadow_hermes_service=FailingShadowHermesService(),
        settings=Settings(hermes_shadow_mode=True, hermes_shadow_sample_rate=1.0),
        random_func=lambda: 0.0,
    )
    message = IncomingMessage(
        channel="telegram",
        external_user_id="shadow-error",
        external_chat_id="shadow-error-chat",
        message_type="text",
        text="Tengo cucarachas en la cocina en Torremolinos",
    )

    response = await service.handle_incoming_message(message)

    shadow_records = await firestore_service.list_documents(
        "shadow_decision_records",
        filters={"conversation_id": "telegram:shadow-error"},
    )
    assert response.action.type == "create_incident"
    assert len(shadow_records) == 1
    assert shadow_records[0]["shadow_action_type"] is None
    assert shadow_records[0]["shadow_error"] == "UnexpectedError:RuntimeError"
    assert shadow_records[0]["agreement_summary"] == "shadow_error"


@pytest.mark.asyncio
async def test_shadow_fallback_reason_is_stored_as_shadow_error() -> None:
    firestore_service = MockFirestoreService()
    service = ConversationService(
        firestore_service=firestore_service,
        shadow_hermes_service=FallbackShadowHermesService(),
        settings=Settings(hermes_shadow_mode=True, hermes_shadow_sample_rate=1.0),
        random_func=lambda: 0.0,
    )
    message = IncomingMessage(
        channel="telegram",
        external_user_id="shadow-fallback",
        external_chat_id="shadow-fallback-chat",
        message_type="text",
        text="Tengo cucarachas en la cocina en Torremolinos",
    )

    response = await service.handle_incoming_message(message)

    shadow_records = await firestore_service.list_documents(
        "shadow_decision_records",
        filters={"conversation_id": "telegram:shadow-fallback"},
    )
    assert response.action.type == "create_incident"
    assert len(shadow_records) == 1
    assert shadow_records[0]["shadow_action_type"] == "escalate_to_human"
    assert shadow_records[0]["shadow_fallback_used"] is True
    assert shadow_records[0]["shadow_error"] == "HermesClientError:connection_error"
    assert (
        shadow_records[0]["metadata"]["shadow_fallback_reason"]
        == "HermesClientError:connection_error"
    )
