import pytest
from app.incidents.status_service import IncidentStatusService
from app.services.mock_firestore_service import MockFirestoreService


def test_is_status_query_patterns() -> None:
    service = IncidentStatusService()
    
    # Consultas válidas
    assert service.is_status_query("cómo va mi incidencia?") is True
    assert service.is_status_query("como va lo mio?") is True
    assert service.is_status_query("quiero ver el estado de mi reporte") is True
    assert service.is_status_query("Hay novedades?") is True
    assert service.is_status_query("hola? hay novedades?") is True
    assert service.is_status_query("qué pasa con mi aviso?") is True
    assert service.is_status_query("mi reporte") is True
    
    # Consultas inválidas
    assert service.is_status_query("hola buenas tardes") is False
    assert service.is_status_query("tengo un problema de ratas") is False
    assert service.is_status_query("") is False
    assert service.is_status_query(None) is False


def test_get_status_message_mappings() -> None:
    service = IncidentStatusService()
    
    msg_pending = service.get_status_message("pending_review")
    assert "pendiente" in msg_pending.lower()
    assert "revisión" in msg_pending.lower() or "revision" in msg_pending.lower()
    
    msg_cancelled = service.get_status_message("cancelled")
    assert "descartada" in msg_cancelled.lower()
    assert "cancelada" in msg_cancelled.lower()
    
    msg_closed = service.get_status_message("closed")
    assert "cerrada" in msg_closed.lower()
    
    msg_in_progress = service.get_status_message("in_progress")
    assert "curso" in msg_in_progress.lower()
    
    # Unknown status fallback
    msg_unknown = service.get_status_message("invalid_status_xyz")
    assert "registrada" in msg_unknown.lower()


@pytest.mark.asyncio
async def test_resolve_status_message_from_db() -> None:
    firestore = MockFirestoreService()
    service = IncidentStatusService(firestore_service=firestore)
    conversation_id = "telegram:test-user-status"
    
    # Caso 1: No hay incidentes
    msg_none = await service.resolve_status_message(conversation_id)
    assert msg_none is None
    
    # Caso 2: Un incidente en pending_review
    inc1 = {
        "id": "inc-1",
        "conversation_id": conversation_id,
        "status": "pending_review",
        "created_at": "2026-06-04T10:00:00Z"
    }
    await firestore.create_document("incidents", inc1)
    msg1 = await service.resolve_status_message(conversation_id)
    assert "pendiente" in msg1.lower()
    
    # Caso 3: Dos incidentes, el más reciente está cancelled
    inc2 = {
        "id": "inc-2",
        "conversation_id": conversation_id,
        "status": "cancelled",
        "created_at": "2026-06-04T11:00:00Z"
    }
    await firestore.create_document("incidents", inc2)
    msg2 = await service.resolve_status_message(conversation_id)
    assert "descartada" in msg2.lower()
