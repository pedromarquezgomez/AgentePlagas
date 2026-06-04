import pytest
from datetime import datetime, timezone
from app.services.mock_firestore_service import MockFirestoreService
from app.services.incident_service import IncidentService
from app.schemas.incident import IncidentDraft
from app.context.builders.incident_builder import IncidentBuilder
from app.adapters.telegram_adapter import TelegramAdapter
from app.schemas.outgoing_message import OutgoingMessage

@pytest.mark.asyncio
async def test_incident_cancellation_proactive_notification(monkeypatch) -> None:
    """Verifica que al cancelar una incidencia se notifique proactivamente al cliente vía Telegram."""
    firestore = MockFirestoreService()
    incident_service = IncidentService(firestore_service=firestore)
    
    # 1. Crear conversación
    conversation_id = "telegram:pedro-123"
    await firestore.create_document(
        "conversations",
        {
            "id": conversation_id,
            "channel": "telegram",
            "external_user_id": "pedro-123",
            "external_chat_id": "chat-123",
            "status": "active",
        },
        document_id=conversation_id,
    )
    
    # 2. Crear incidencia
    draft = IncidentDraft(
        conversation_id=conversation_id,
        channel="telegram",
        pest_type="COCKROACH",
        location="Calle Larios 5, Málaga",
        affected_area="cocina",
        priority="medium",
        summary="Cucarachas en la cocina",
    )
    incident = await incident_service.create_incident(draft)
    
    # 3. Interceptar send_message del adaptador
    sent_messages = []
    async def mock_send_message(self, outgoing_message: OutgoingMessage) -> dict:
        sent_messages.append(outgoing_message)
        return {"status": "ok"}
        
    monkeypatch.setattr(TelegramAdapter, "send_message", mock_send_message)
    
    # 4. Actualizar estado a cancelado
    await incident_service.update_incident(incident.id, {"status": "cancelled"})
    
    # Validar que se envió la notificación
    assert len(sent_messages) == 1
    assert sent_messages[0].channel == "telegram"
    assert sent_messages[0].external_chat_id == "chat-123"
    assert "descartada" in sent_messages[0].text
    assert "cucarachas" in sent_messages[0].text


@pytest.mark.asyncio
async def test_incident_builder_context_for_cancelled_incident(monkeypatch) -> None:
    """Verifica que IncidentBuilder inyecta el prefijo de descartado cuando el incidente más reciente está cancelado."""
    firestore = MockFirestoreService()
    incident_service = IncidentService(firestore_service=firestore)
    builder = IncidentBuilder(firestore_service=firestore)
    
    conversation_id = "telegram:pedro-123"
    
    # Mockear el envío de mensajes de Telegram para evitar llamadas reales a la API
    async def mock_send_message(self, outgoing_message: OutgoingMessage) -> dict:
        return {"status": "ok"}
    monkeypatch.setattr(TelegramAdapter, "send_message", mock_send_message)
    
    # 1. Crear incidencia cancelada
    draft = IncidentDraft(
        conversation_id=conversation_id,
        channel="telegram",
        pest_type="COCKROACH",
        location="Calle Larios 5, Málaga",
        affected_area="cocina",
        priority="medium",
        summary="Cucarachas en la cocina",
    )
    incident = await incident_service.create_incident(draft)
    await incident_service.update_incident(incident.id, {"status": "cancelled"})
    
    # 2. Construir contexto
    inc_id, inc_summary = await builder.build(conversation_id)
    
    assert inc_id == incident.id
    assert inc_summary is not None
    assert "[ESTADO: DESCARTADO/CANCELADO]" in inc_summary
    assert "Cucarachas en la cocina" in inc_summary
