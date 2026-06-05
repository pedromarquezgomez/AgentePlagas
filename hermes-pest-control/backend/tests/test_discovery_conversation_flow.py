import pytest
from app.schemas.incoming_message import IncomingMessage
from app.services.conversation_service import ConversationService
from app.services.firestore_factory import get_firestore_service
from app.diagnostics.contracts import DiagnosisState
from datetime import datetime, timezone

def _incoming_message(text: str, external_user_id: str = "user-disc-1") -> IncomingMessage:
    return IncomingMessage(
        channel="telegram",
        external_user_id=external_user_id,
        external_chat_id="chat-disc-1",
        message_type="text",
        text=text,
        attachments=[],
        metadata={},
    )

@pytest.mark.asyncio
async def test_discovery_conversation_multiturn_flow() -> None:
    firestore = get_firestore_service()
    service = ConversationService(firestore_service=firestore)
    conversation_id = "telegram:user-disc-1"

    # Limpiar conversaciones
    await firestore.update_document("conversations", conversation_id, {"conversation_state": {"phase": "IDLE"}})

    # Sembrar el cliente
    await firestore.create_document(
        "customers",
        {
            "id": "cust-disc",
            "name": "Pedro",
            "telegram_user_id": "user-disc-1",
        },
        document_id="cust-disc"
    )

    # Turno 1: Mensaje indicando plaga conocida directa ("cucarachas")
    msg1 = _incoming_message("Tengo cucarachas")
    response1 = await service.handle_incoming_message(msg1)

    assert response1.action.type == "technical_discovery"
    # No debe pedir datos de admisión
    assert "nombre de contacto" not in response1.reply
    assert "dirección" not in response1.reply
    assert "localidad" not in response1.reply
    assert "vivienda" in response1.reply or "negocio" in response1.reply

    # Verificar que el estado DISCOVERY se haya persistido en Firestore
    conv_doc = await firestore.get_document("conversations", conversation_id)
    assert conv_doc is not None
    assert conv_doc["conversation_state"]["phase"] == "DISCOVERY"
    assert conv_doc["conversation_state"]["discovery"]["knowledge_key"] == "cockroaches"
    assert conv_doc["conversation_state"]["discovery"]["environment_type"] is None

    # Turno 2: Respuesta con el tipo de entorno ("En un restaurante")
    msg2 = _incoming_message("En un restaurante")
    response2 = await service.handle_incoming_message(msg2)

    assert response2.action.type == "technical_discovery"
    # Debe seguir en DISCOVERY
    conv_doc2 = await firestore.get_document("conversations", conversation_id)
    assert conv_doc2["conversation_state"]["phase"] == "DISCOVERY"
    assert conv_doc2["conversation_state"]["discovery"]["environment_type"] == "negocio"
    assert conv_doc2["conversation_state"]["discovery"]["business_type"] == "restaurante"

    # Turno 3: Respuesta con la zona afectada ("En cocina")
    msg3 = _incoming_message("En cocina")
    response3 = await service.handle_incoming_message(msg3)

    # Debe seguir en DISCOVERY y preguntar por la gravedad/tiempo
    assert response3.action.type == "technical_discovery"
    conv_doc3 = await firestore.get_document("conversations", conversation_id)
    assert conv_doc3["conversation_state"]["phase"] == "DISCOVERY"
    assert conv_doc3["conversation_state"]["discovery"]["affected_zone"] == "cocina"

    # Turno 4: Respuesta con gravedad/tiempo ("desde hace dos días y son muchas")
    msg4 = _incoming_message("desde hace dos días y son muchas")
    response4 = await service.handle_incoming_message(msg4)

    # Al tener entorno, zona y gravedad/tiempo, transiciona a INTAKE y pide localización/nombre
    assert response4.action.type == "collect_missing_data"
    assert "location" in response4.action.missing_fields
    conv_doc4 = await firestore.get_document("conversations", conversation_id)
    assert conv_doc4["conversation_state"]["phase"] == "INTAKE"
