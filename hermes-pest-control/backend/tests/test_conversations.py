from fastapi.testclient import TestClient
from app.main import app
from app.services.firestore_factory import get_firestore_service

client = TestClient(app)


def test_conversations_lifecycle() -> None:
    mock_db = get_firestore_service()
    mock_db._collections.clear()

    # 1. Crear datos iniciales en mock DB directamente
    mock_db._collections["conversations"] = {
        "conv-1": {
            "id": "conv-1",
            "channel": "telegram",
            "external_user_id": "user123",
            "external_chat_id": "chat123",
            "status": "active",
            "created_at": "2026-06-05T09:00:00Z",
        }
    }
    
    mock_db._collections["messages"] = {
        "msg-1": {
            "id": "msg-1",
            "conversation_id": "conv-1",
            "direction": "inbound",
            "channel": "telegram",
            "text": "Hola, necesito asistencia",
            "created_at": "2026-06-05T09:00:00Z",
        }
    }

    # 2. Listar conversaciones
    response_convs = client.get("/conversations")
    assert response_convs.status_code == 200
    assert len(response_convs.json()) == 1
    assert response_convs.json()[0]["id"] == "conv-1"

    # 3. Listar mensajes de conversación
    response_msgs = client.get("/conversations/conv-1/messages")
    assert response_msgs.status_code == 200
    assert len(response_msgs.json()) == 1
    assert response_msgs.json()[0]["text"] == "Hola, necesito asistencia"

    # 4. Enviar un nuevo mensaje (outbound)
    response_send = client.post(
        "/conversations/conv-1/messages",
        json={"text": "Hola, en qué puedo ayudarte?"},
    )
    assert response_send.status_code == 201
    body_send = response_send.json()
    assert body_send["direction"] == "outbound"
    assert body_send["text"] == "Hola, en qué puedo ayudarte?"

    # 5. Listar de nuevo (debe haber 2 mensajes)
    response_msgs_updated = client.get("/conversations/conv-1/messages")
    assert len(response_msgs_updated.json()) == 2
