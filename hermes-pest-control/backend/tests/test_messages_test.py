from fastapi.testclient import TestClient

from app.main import app
from app.routes import messages_test as messages_test_route


client = TestClient(app)


def _message_payload(text: str) -> dict:
    return {
        "channel": "telegram",
        "external_user_id": "12345",
        "external_chat_id": "67890",
        "message_type": "text",
        "text": text,
        "attachments": [],
        "metadata": {},
    }


def test_messages_test_complete_case_creates_incident() -> None:
    response = client.post(
        "/messages/test",
        json=_message_payload(
            "Tengo cucarachas en la cocina en Torremolinos desde hace una semana"
        ),
    )

    body = response.json()

    assert response.status_code == 200
    assert body["action"]["type"] == "create_incident"
    assert body["incident"]["pest_type"] == "cucarachas"
    assert body["incident"]["location"] == "Torremolinos"
    assert body["incident"]["affected_area"] == "cocina"
    assert body["incident"]["status"] == "pending_review"


def test_messages_test_incomplete_case_collects_missing_data() -> None:
    response = client.post("/messages/test", json=_message_payload("Tengo cucarachas"))

    body = response.json()

    assert response.status_code == 200
    assert body["action"]["type"] == "collect_missing_data"
    assert "affected_area" in body["action"]["missing_fields"]
    assert "location" in body["action"]["missing_fields"]
    assert body["incident"]["should_create"] is False


def test_messages_test_disabled_in_production(monkeypatch) -> None:
    monkeypatch.setattr(messages_test_route.settings, "app_env", "production")

    response = client.post("/messages/test", json=_message_payload("Tengo cucarachas"))

    assert response.status_code == 404
