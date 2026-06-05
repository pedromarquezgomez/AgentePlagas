import pytest
from app.schemas.incoming_message import IncomingMessage
from app.services.conversation_service import ConversationService
from app.services.firestore_factory import get_firestore_service
from app.diagnostics.contracts import DiagnosisState
from datetime import datetime, timezone

def _incoming_message(text: str, external_user_id: str = "user-diag-1") -> IncomingMessage:
    return IncomingMessage(
        channel="telegram",
        external_user_id=external_user_id,
        external_chat_id="chat-diag-1",
        message_type="text",
        text=text,
        attachments=[],
        metadata={},
    )

@pytest.mark.asyncio
async def test_diagnosis_conversation_multiturn_flow() -> None:
    firestore = get_firestore_service()
    service = ConversationService(firestore_service=firestore)
    conversation_id = "telegram:user-diag-1"

    # Sembrar el cliente y una incidencia anterior con ubicación en la BD global de Firestore
    await firestore.create_document(
        "customers",
        {
            "id": "cust-diag",
            "name": "Pedro",
            "telegram_user_id": "user-diag-1",
        },
        document_id="cust-diag"
    )
    await firestore.create_document(
        "incidents",
        {
            "id": "inc-prev-diag",
            "customer_id": "cust-diag",
            "location": "Málaga",
            "pest_type": "COCKROACH",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        document_id="inc-prev-diag"
    )

    # Turno 1: Mensaje ambiguo de plaga en limonero
    msg1 = _incoming_message("Tengo unos bichos verdes en un limonero")
    response1 = await service.handle_incoming_message(msg1)

    assert response1.action.type == "technical_diagnosis"
    assert "pulgón" in response1.reply or "cochinilla" in response1.reply
    # No debe pedir datos de admisión
    assert "nombre de contacto" not in response1.reply
    assert "dirección" not in response1.reply
    assert response1.incident is None or response1.incident.should_create is False

    # Verificar que el estado DIAGNOSIS se haya persistido en Firestore
    conv_doc = await firestore.get_document("conversations", conversation_id)
    assert conv_doc is not None
    assert conv_doc["conversation_state"]["phase"] == "DIAGNOSIS"
    assert conv_doc["conversation_state"]["diagnosis"]["knowledge_key"] == "plant_pests"

    # Turno 2: Respuesta afirmativa a preguntas de diagnóstico
    msg2 = _incoming_message("Sí, están agrupados y las hojas pegajosas")
    response2 = await service.handle_incoming_message(msg2)

    # Debe transicionar a INTAKE y proponer la creación de la incidencia
    assert response2.action.type == "create_incident"
    assert "pulgón" in response2.reply
    assert "compatible" in response2.reply
    assert "aviso" in response2.reply or "registrado" in response2.reply

    # Verificar que la fase se haya limpiado o transicionado a INTAKE/IDLE
    conv_doc2 = await firestore.get_document("conversations", conversation_id)
    assert conv_doc2["conversation_state"]["phase"] == "INTAKE"
