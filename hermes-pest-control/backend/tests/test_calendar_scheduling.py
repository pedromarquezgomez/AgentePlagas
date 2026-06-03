import anyio
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from app.main import app
from app.config.settings import Settings
from app.schemas.incoming_message import IncomingMessage
from app.services.conversation_service import ConversationService
from app.services.mock_firestore_service import MockFirestoreService
from app.policies.engine import PolicyEngine
from app.policies.contracts import PolicyContext, PolicyDecision
from app.audit.contracts import AuditEventType
from app.calendar.availability_service import AvailabilityService
from app.calendar.calendar_service import HermesCalendarService
from app.calendar.contracts import CalendarEventDraft
from app.services.tool_execution_service import ToolExecutionService

client = TestClient(app)


def test_calendar_policy_decisions() -> None:
    """Verifica que schedule_visit_tool requiere revisión humana inicialmente."""
    engine = PolicyEngine()
    
    ctx_visit = PolicyContext(requested_tool="schedule_visit_tool")
    eval_visit = engine.evaluate(ctx_visit)
    assert eval_visit.decision == PolicyDecision.REQUIRE_HUMAN_REVIEW


def test_availability_service_logic() -> None:
    """Verifica que AvailabilityService calcula los huecos omitiendo fines de semana y fuera de horario laboral."""
    # 1. Definir ocupaciones
    # Supongamos que mañana es Lunes
    now = datetime.now(timezone.utc)
    # Buscamos el próximo lunes
    next_lunes = now + timedelta(days=(7 - now.weekday()) if now.weekday() >= 0 else 1)
    next_lunes = datetime(next_lunes.year, next_lunes.month, next_lunes.day, tzinfo=timezone.utc)
    
    # Supongamos que el lunes de 09:00 a 10:00 está ocupado
    busy_start = next_lunes.replace(hour=9, minute=0)
    busy_end = next_lunes.replace(hour=10, minute=0)
    
    free_slots = AvailabilityService.calculate_free_slots(
        busy_slots=[(busy_start, busy_end)],
        start_date=next_lunes,
        duration_minutes=60,
        max_slots=3,
    )
    
    assert len(free_slots) == 3
    # El primer slot libre debería ser el lunes a las 10:00 (ya que 09:00-10:00 está ocupado)
    slot1_dt = datetime.fromisoformat(free_slots[0])
    assert slot1_dt.hour == 10
    assert slot1_dt.minute == 0
    # Los siguientes slots son 11:00 y 12:00
    slot2_dt = datetime.fromisoformat(free_slots[1])
    assert slot2_dt.hour == 11
    slot3_dt = datetime.fromisoformat(free_slots[2])
    assert slot3_dt.hour == 12


@pytest.mark.asyncio
async def test_auto_proposal_of_visit_scheduling() -> None:
    """Verifica que ante un mensaje se proponga la visita en tool_execution_records."""
    firestore = MockFirestoreService()
    settings = Settings(agent_provider="mock", hermes_mode="mock")
    service = ConversationService(firestore_service=firestore, settings=settings)
    
    message = IncomingMessage(
        channel="telegram",
        external_user_id="pedro-123",
        external_chat_id="chat-123",
        message_type="text",
        text=(
            "Tengo cucarachas en la cocina de mi restaurante. Mi nombre es Pedro. "
            "Estamos en Calle Larios 5, Málaga. Mi correo es pmarquez.particular@gmail.com"
        ),
        attachments=[],
        metadata={},
    )
    
    response = await service.handle_incoming_message(message)
    
    # Verificar que se propuso crear la incidencia y se asignó prioridad
    assert response.incident is not None
    
    # 2. Verificar que se propuso la herramienta schedule_visit_tool en Firestore
    executions = await firestore.list_documents("tool_execution_records")
    visit_executions = [e for e in executions if e.get("tool_name") == "schedule_visit_tool"]
    assert len(visit_executions) == 1
    
    visit_record = visit_executions[0]
    assert visit_record["requires_approval"] is True
    assert visit_record["decision"] == "require_human_approval"
    assert visit_record["execution_status"] == "pending_human_approval"
    assert visit_record["review_status"] == "proposed"
    
    payload = visit_record["approved_payload"]
    assert payload["customer_name"] == "Pedro"
    assert payload["customer_email"] == "pmarquez.particular@gmail.com"
    assert payload["location"] == "Málaga"
    assert payload["visit_type"] == "URGENT_TREATMENT"
    assert payload["pest_type"] == "cucarachas"
    assert len(payload["proposed_slots"]) == 3
    assert payload["selected_slot"] == payload["proposed_slots"][0]
    
    # 3. Verificar auditoría de propuesta
    events = service.audit_service.list_events()
    event_types = [e.event_type for e in events]
    assert AuditEventType.TOOL_PROPOSED in event_types
    assert AuditEventType.POLICY_EVALUATED in event_types
    assert AuditEventType.HUMAN_REVIEW_REQUIRED in event_types


@pytest.mark.asyncio
async def test_execute_visit_scheduling_after_approval() -> None:
    """Verifica que no se crea el evento sin confirmación, y se crea tras aprobación."""
    firestore = MockFirestoreService()
    execution_service = ToolExecutionService(firestore_service=firestore)
    
    # Crear un record propuesto
    record_id = "test-execution-schedule-visit"
    now_iso = datetime.now(timezone.utc).isoformat()
    tool_payload = {
        "incident_id": "incident-abc",
        "customer_name": "Pedro",
        "customer_email": "pmarquez.particular@gmail.com",
        "location": "Calle Larios 5, Málaga",
        "visit_type": "URGENT_TREATMENT",
        "pest_type": "COCKROACH",
        "duration_minutes": 60,
        "proposed_slots": [now_iso],
        "selected_slot": now_iso,
    }
    
    from app.schemas.tool_harness import ToolExecutionRecord
    record = ToolExecutionRecord(
        id=record_id,
        tool_request_id="req-1",
        tool_decision_id="dec-1",
        trace_id="trace-1",
        conversation_id="telegram:pedro-123",
        tool_name="schedule_visit_tool",
        provider="calendar",
        action="schedule_visit",
        risk_level=3,
        requires_approval=True,
        decision="require_human_approval",
        execution_status="pending_human_approval",
        review_status="proposed",
        approved_payload=tool_payload,
        metadata={"payload": tool_payload},
    )
    
    await execution_service.create_execution_record(record)
    
    # 1. No crear evento sin confirmación (debe lanzar error si review_status != approved)
    with pytest.raises(Exception) as exc_info:
        await execution_service.execute_execution_record(record_id)
    assert "requires review_status=approved" in str(exc_info.value)
    
    # 2. Aprobar
    from app.schemas.tool_harness import ToolExecutionRecordUpdate
    await execution_service.update_execution_record(
        record_id,
        ToolExecutionRecordUpdate(review_status="approved")
    )
    
    # 3. Ejecutar tras aprobación
    updated_record = await execution_service.execute_execution_record(record_id)
    assert updated_record["executed"] is True
    assert updated_record["execution_status"] == "executed"
    
    result = updated_record["execution_result"]
    assert result["event_id"] == "mock-event-id-12345"
    assert "Pedro" in result["title"]
    assert "COCKROACH" in result["title"]
    assert "incident-abc" in result["description"]
    assert "Calle Larios 5" in result["location"]
    
    # Verificar que se registró auditoría de ejecución
    events = execution_service.audit_service.list_events()
    event_types = [e.event_type for e in events]
    assert AuditEventType.TOOL_EXECUTION_STARTED in event_types
    assert AuditEventType.TOOL_EXECUTION_COMPLETED in event_types
