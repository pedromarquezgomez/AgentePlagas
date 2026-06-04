import pytest
from datetime import datetime, timezone

from app.config.settings import Settings
from app.schemas.incoming_message import IncomingMessage
from app.schemas.tool_harness import ToolExecutionRecord
from app.services.conversation_service import ConversationService
from app.services.mock_firestore_service import MockFirestoreService
from app.calendar.selection_service import VisitSlotSelectionService


def test_interpret_selection_cases() -> None:
    service = VisitSlotSelectionService()

    # Caso 1: primera opción y variantes
    assert service.interpret_selection("Me viene mejor la primera opción") == 1
    assert service.interpret_selection("opción 1 por favor") == 1
    assert service.interpret_selection("Prefiero el primer horario") == 1
    assert service.interpret_selection("primera opcion") == 1

    # Caso 2: segunda opción y variantes
    assert service.interpret_selection("Elijo la segunda opción") == 2
    assert service.interpret_selection("opción 2") == 2
    assert service.interpret_selection("segundo horario es mejor") == 2

    # Caso 3: opción 3 y variantes
    assert service.interpret_selection("La tercera opción me va bien") == 3
    assert service.interpret_selection("opción 3") == 3
    assert service.interpret_selection("tercer horario") == 3

    # Texto no relacionado o vacío
    assert service.interpret_selection("hola buenos días") is None
    assert service.interpret_selection("") is None
    assert service.interpret_selection(None) is None

    # Caso 6: Texto ambiguo (múltiples coincidencias)
    assert service.interpret_selection("opción 1 o segunda opción") is None


@pytest.mark.asyncio
async def test_resolve_selection_no_active_proposal() -> None:
    # Caso 4: Sin propuesta activa -> retornar None
    firestore = MockFirestoreService()
    service = VisitSlotSelectionService(firestore_service=firestore)
    
    res = await service.resolve_selection("telegram:user-1", "primera opción")
    assert res is None


@pytest.mark.asyncio
async def test_resolve_selection_valid_proposal() -> None:
    # Caso 5: Propuesta activa + selección válida
    firestore = MockFirestoreService()
    service = VisitSlotSelectionService(firestore_service=firestore)
    conversation_id = "telegram:user-2"
    
    # Crear propuesta en tool_execution_records
    proposal = {
        "id": "record-1",
        "tool_request_id": "req-1",
        "tool_decision_id": "dec-1",
        "trace_id": "trace-1",
        "conversation_id": conversation_id,
        "tool_name": "schedule_visit_tool",
        "provider": "calendar",
        "action": "schedule_visit",
        "risk_level": 3,
        "requires_approval": True,
        "decision": "require_human_approval",
        "execution_status": "pending_human_approval",
        "review_status": "proposed",
        "approved_payload": {
            "proposed_slots": [
                "2026-06-05T09:00:00Z",
                "2026-06-05T10:00:00Z",
                "2026-06-05T11:00:00Z"
            ]
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await firestore.create_document("tool_execution_records", proposal)
    
    res = await service.resolve_selection(conversation_id, "segunda opción")
    assert res is not None
    assert res.slot_index == 2
    assert res.start_time == "2026-06-05T10:00:00Z"
    assert res.end_time == "2026-06-05T11:00:00Z"


@pytest.mark.asyncio
async def test_integration_slot_selection_success() -> None:
    firestore = MockFirestoreService()
    settings = Settings(agent_provider="mock", hermes_mode="mock")
    conversation_service = ConversationService(
        firestore_service=firestore,
        settings=settings,
    )
    
    conversation_id = "telegram:pedro"
    external_user_id = "pedro"
    external_chat_id = "pedro-chat"
    
    # Inyectar una propuesta en Firestore
    proposal = {
        "id": "exec-123",
        "tool_request_id": "req-123",
        "tool_decision_id": "dec-123",
        "trace_id": "trace-123",
        "conversation_id": conversation_id,
        "tool_name": "schedule_visit_tool",
        "provider": "calendar",
        "action": "schedule_visit",
        "risk_level": 3,
        "requires_approval": True,
        "decision": "require_human_approval",
        "execution_status": "pending_human_approval",
        "review_status": "proposed",
        "approved_payload": {
            "incident_id": "inc-123",
            "proposed_slots": [
                "2026-06-05T09:00:00Z",
                "2026-06-05T10:00:00Z",
                "2026-06-05T11:00:00Z"
            ]
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await firestore.create_document("tool_execution_records", proposal)
    
    message = IncomingMessage(
        channel="telegram",
        external_user_id=external_user_id,
        external_chat_id=external_chat_id,
        message_type="text",
        text="Me viene mejor la primera opción",
    )
    
    response = await conversation_service.handle_incoming_message(message)
    
    # Validar respuesta conversacional
    assert "registrado" in response.reply.lower() or "preferencia" in response.reply.lower()
    assert response.action.type == "schedule_visit_selection"
    
    # Validar que se actualizó el payload en Firestore
    updated_record = await firestore.get_document("tool_execution_records", "exec-123")
    payload = updated_record["approved_payload"]
    assert "selected_slot" in payload
    assert payload["selected_slot"]["slot_index"] == 1
    assert payload["selected_slot"]["start_time"] == "2026-06-05T09:00:00Z"


@pytest.mark.asyncio
async def test_integration_slot_selection_ambiguous() -> None:
    firestore = MockFirestoreService()
    settings = Settings(agent_provider="mock", hermes_mode="mock")
    conversation_service = ConversationService(
        firestore_service=firestore,
        settings=settings,
    )
    
    conversation_id = "telegram:pedro"
    external_user_id = "pedro"
    external_chat_id = "pedro-chat"
    
    # Inyectar una propuesta en Firestore
    proposal = {
        "id": "exec-123",
        "tool_request_id": "req-123",
        "tool_decision_id": "dec-123",
        "trace_id": "trace-123",
        "conversation_id": conversation_id,
        "tool_name": "schedule_visit_tool",
        "provider": "calendar",
        "action": "schedule_visit",
        "risk_level": 3,
        "requires_approval": True,
        "decision": "require_human_approval",
        "execution_status": "pending_human_approval",
        "review_status": "proposed",
        "approved_payload": {
            "proposed_slots": [
                "2026-06-05T09:00:00Z",
                "2026-06-05T10:00:00Z",
                "2026-06-05T11:00:00Z"
            ]
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await firestore.create_document("tool_execution_records", proposal)
    
    message = IncomingMessage(
        channel="telegram",
        external_user_id=external_user_id,
        external_chat_id=external_chat_id,
        message_type="text",
        text="opción 1 o la segunda opción",
    )
    
    response = await conversation_service.handle_incoming_message(message)
    assert "no he entendido cuál de las opciones" in response.reply.lower()
    assert response.action.type == "collect_missing_data"
