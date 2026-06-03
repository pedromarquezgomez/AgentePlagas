import pytest

from app.schemas.incoming_message import IncomingMessage
from app.services.conversation_service import ConversationService
from app.services.mock_firestore_service import MockFirestoreService
from app.audit.contracts import AuditEventType


def _incoming_message(text: str, external_user_id: str = "user-123") -> IncomingMessage:
    return IncomingMessage(
        channel="telegram",
        external_user_id=external_user_id,
        external_chat_id="chat-123",
        message_type="text",
        text=text,
        attachments=[],
        metadata={},
    )


@pytest.mark.asyncio
async def test_incomplete_message_requests_missing_info() -> None:
    # Test 1: Mensaje incompleto
    # Debe solicitar información de ubicación y nombre.
    firestore = MockFirestoreService()
    service = ConversationService(firestore_service=firestore)
    message = _incoming_message("Tengo cucarachas", external_user_id="user-1")

    response = await service.handle_incoming_message(message)

    assert response.action.type == "collect_missing_data"
    assert "location" in response.action.missing_fields
    assert "customer_name" in response.action.missing_fields
    assert "ubicación" in response.reply
    assert "nombre de contacto" in response.reply
    assert response.incident is None or response.incident.should_create is False


@pytest.mark.asyncio
async def test_partially_complete_message_requests_remaining_data() -> None:
    # Test 2: Mensaje parcialmente completo
    # Debe solicitar el dato restante (contacto).
    firestore = MockFirestoreService()
    service = ConversationService(firestore_service=firestore)
    message = _incoming_message("Tengo cucarachas en la cocina del local central.", external_user_id="user-2")

    response = await service.handle_incoming_message(message)

    assert response.action.type == "collect_missing_data"
    assert "customer_name" in response.action.missing_fields
    assert "location" not in response.action.missing_fields
    assert "nombre de contacto" in response.reply


@pytest.mark.asyncio
async def test_complete_message_proposes_create_incident() -> None:
    # Test 3: Información completa
    # Debe proponer la creación de incidencia.
    firestore = MockFirestoreService()
    service = ConversationService(firestore_service=firestore)
    message = _incoming_message("Tengo cucarachas en la cocina del local central. Mi nombre es Carlos.", external_user_id="user-3")

    response = await service.handle_incoming_message(message)

    assert response.action.type == "create_incident"
    assert not response.action.missing_fields
    assert response.incident is not None
    assert response.incident.should_create is True
    assert response.incident.pest_type == "cockroach"
    assert response.incident.location == "cocina del local central"


@pytest.mark.asyncio
async def test_multi_turn_flow_reconstructs_state_and_creates_incident() -> None:
    # Test 4: Flujo completo multi-turno
    # Mensaje 1: "Tengo cucarachas"
    # Mensaje 2: "Es en la cocina del local"
    # Mensaje 3: "Soy Carlos"
    # Debe terminar creando la incidencia.
    firestore = MockFirestoreService()
    service = ConversationService(firestore_service=firestore)
    user_id = "user-4"

    # Turno 1
    msg1 = _incoming_message("Tengo cucarachas", external_user_id=user_id)
    resp1 = await service.handle_incoming_message(msg1)
    assert resp1.action.type == "collect_missing_data"

    # Turno 2
    msg2 = _incoming_message("Es en la cocina del local", external_user_id=user_id)
    resp2 = await service.handle_incoming_message(msg2)
    assert resp2.action.type == "collect_missing_data"

    # Turno 3
    msg3 = _incoming_message("Soy Carlos", external_user_id=user_id)
    resp3 = await service.handle_incoming_message(msg3)

    # Validaciones finales
    assert resp3.action.type == "create_incident"
    assert resp3.incident is not None
    assert resp3.incident.should_create is True
    assert resp3.incident.pest_type == "cockroach"
    assert resp3.incident.location == "cocina del local"
    assert resp3.incident.id is not None

    # Verificar que el incidente real existe en base de datos
    incident_in_db = await service.incident_service.get_incident(resp3.incident.id)
    assert incident_in_db is not None
    assert incident_in_db["pest_type"] == "cockroach"
    assert incident_in_db["location"] == "cocina del local"


@pytest.mark.asyncio
async def test_incident_creation_generates_audit_events() -> None:
    # Test 5: Incidencia creada con eventos de auditoría.
    # Debe registrar: TOOL_PROPOSED, POLICY_EVALUATED, TOOL_EXECUTION_STARTED, TOOL_EXECUTION_COMPLETED
    firestore = MockFirestoreService()
    service = ConversationService(firestore_service=firestore)
    message = _incoming_message("Tengo cucarachas en la cocina del local central. Mi nombre es Carlos.", external_user_id="user-5")

    response = await service.handle_incoming_message(message)

    assert response.action.type == "create_incident"

    # Obtener eventos de auditoría del audit_service
    events = service.audit_service.list_events()
    event_types = [event.event_type for event in events]

    assert AuditEventType.TOOL_PROPOSED in event_types
    assert AuditEventType.POLICY_EVALUATED in event_types
    assert AuditEventType.TOOL_EXECUTION_STARTED in event_types
    assert AuditEventType.TOOL_EXECUTION_COMPLETED in event_types
