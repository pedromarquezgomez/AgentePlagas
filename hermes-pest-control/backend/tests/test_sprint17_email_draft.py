import anyio
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config.settings import Settings
from app.schemas.incoming_message import IncomingMessage
from app.services.conversation_service import ConversationService
from app.services.mock_firestore_service import MockFirestoreService
from app.policies.engine import PolicyEngine
from app.policies.contracts import PolicyContext, PolicyDecision
from app.audit.contracts import AuditEventType

client = TestClient(app)


def test_gmail_policy_decisions() -> None:
    """Verifica que gmail.create_draft requiere revisión humana y gmail.send_email está denegado."""
    engine = PolicyEngine()
    
    ctx_draft = PolicyContext(requested_tool="gmail.create_draft")
    eval_draft = engine.evaluate(ctx_draft)
    assert eval_draft.decision == PolicyDecision.REQUIRE_HUMAN_REVIEW
    
    ctx_send = PolicyContext(requested_tool="gmail.send_email")
    eval_send = engine.evaluate(ctx_send)
    assert eval_send.decision == PolicyDecision.DENY


def test_config_status_contains_sprint17_keys() -> None:
    """Verifica que GET /config/status retorne las variables solicitadas para verificar producción."""
    response = client.get("/config/status")
    assert response.status_code == 200
    body = response.json()
    assert "fallback_provider" in body
    assert "shadow_mode" in body
    assert body["fallback_provider"] == "mock"
    assert body["shadow_mode"] is False


@pytest.mark.asyncio
async def test_auto_proposal_of_gmail_draft_on_email_message() -> None:
    """Verifica que ante un mensaje con email se cree la incidencia y se proponga el borrador de Gmail."""
    firestore = MockFirestoreService()
    settings = Settings(agent_provider="mock", hermes_mode="mock")
    service = ConversationService(firestore_service=firestore, settings=settings)
    
    # Mensaje con correo electrónico de Pedro
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
    
    # Procesar mensaje
    response = await service.handle_incoming_message(message)
    
    # 1. Verificar que se propuso crear la incidencia
    assert response.action.type == "escalate_to_human"
    assert response.incident is not None
    assert response.incident.pest_type == "cucarachas"
    assert response.incident.priority == "urgent"
    assert response.incident.sla_hours == 24
    assert response.incident.dispatch_bucket == "URGENT_24H"
    
    # 2. Verificar que se propuso el borrador en Firestore
    executions = await firestore.list_documents("tool_execution_records")
    assert len(executions) >= 1
    
    # Encontrar la propuesta de borrador de gmail
    gmail_executions = [e for e in executions if e.get("tool_name") == "gmail.create_draft"]
    assert len(gmail_executions) == 1
    
    gmail_record = gmail_executions[0]
    assert gmail_record["requires_approval"] is True
    assert gmail_record["decision"] == "require_human_approval"
    assert gmail_record["execution_status"] == "pending_human_approval"
    assert gmail_record["review_status"] == "proposed"
    
    payload = gmail_record["approved_payload"]
    assert payload["recipient"] == "pmarquez.particular@gmail.com"
    assert payload["subject"] == "Incidencia registrada — control de plagas"
    
    # Validar partes importantes del cuerpo
    body = payload["body"]
    assert "Hola Pedro," in body
    assert "Tipo de plaga: cucarachas" in body
    assert "Ubicación: Málaga" in body
    assert "Zona afectada: cocina" in body
    assert "Prioridad: urgente" in body
    assert "SLA recomendado: 24 horas" in body
    assert "Tipo de actuación recomendada: tratamiento urgente" in body
    
    # 3. Verificar auditoría
    events = service.audit_service.list_events()
    event_types = [e.event_type for e in events]
    assert AuditEventType.TOOL_PROPOSED in event_types
    assert AuditEventType.POLICY_EVALUATED in event_types
    assert AuditEventType.HUMAN_REVIEW_REQUIRED in event_types
