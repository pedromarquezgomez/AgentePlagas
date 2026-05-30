import pytest
from pydantic import ValidationError

from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage


def test_incoming_message_fails_without_channel() -> None:
    with pytest.raises(ValidationError):
        IncomingMessage(
            external_user_id="12345",
            external_chat_id="67890",
            message_type="text",
            text="Tengo cucarachas",
        )


def test_incoming_message_fails_with_unknown_channel() -> None:
    with pytest.raises(ValidationError):
        IncomingMessage(
            channel="fax",
            external_user_id="12345",
            external_chat_id="67890",
            message_type="text",
            text="Tengo cucarachas",
        )


def test_agent_response_accepts_valid_create_incident() -> None:
    response = AgentResponse(
        reply="Incidencia preparada.",
        action={"type": "create_incident", "missing_fields": []},
        incident={
            "should_create": True,
            "pest_type": "cucarachas",
            "location": "Torremolinos",
            "affected_area": "cocina",
            "priority": "high",
            "summary": "Cliente informa de cucarachas.",
        },
    )

    assert response.action.type == "create_incident"
    assert response.incident is not None
    assert response.incident.should_create is True


def test_agent_response_rejects_unknown_action_type() -> None:
    with pytest.raises(ValidationError):
        AgentResponse(
            reply="Respuesta inválida.",
            action={"type": "unsupported_action", "missing_fields": []},
            incident={"should_create": False},
        )

