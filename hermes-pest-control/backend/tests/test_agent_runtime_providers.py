import json

import httpx
import pytest

from app.config.settings import Settings
from app.harness.contracts import AgentRuntimeRequest
from app.harness.providers.hermes_http_provider import HermesHttpRuntimeProvider
from app.harness.providers.mock_provider import MockAgentRuntimeProvider
from app.schemas.incoming_message import IncomingMessage


def _incoming_message(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel="telegram",
        external_user_id="runtime-user",
        external_chat_id="runtime-chat",
        message_type="text",
        text=text,
        attachments=[],
        metadata={},
    )


@pytest.mark.asyncio
async def test_mock_runtime_provider_returns_agent_response() -> None:
    provider = MockAgentRuntimeProvider()
    request = AgentRuntimeRequest(
        incoming_message=_incoming_message(
            "Tengo cucarachas en la cocina en Torremolinos"
        ),
        business_context={"conversation_id": "telegram:runtime-user"},
    )

    response = await provider.process(request)

    assert provider.mode == "mock"
    assert response.action.type == "create_incident"
    assert response.incident is not None
    assert response.incident.pest_type == "cucarachas"


@pytest.mark.asyncio
async def test_hermes_http_runtime_provider_uses_agent_response_contract() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.read())
        return httpx.Response(
            200,
            json={
                "reply": "Respuesta desde provider HTTP.",
                "action": {"type": "collect_missing_data", "missing_fields": ["location"]},
                "incident": {"should_create": False},
            },
        )

    provider = HermesHttpRuntimeProvider(
        Settings(
            hermes_mode="real",
            hermes_api_url="https://hermes-agent.test/agent",
        ),
        transport=httpx.MockTransport(handler),
    )
    request = AgentRuntimeRequest(
        incoming_message=_incoming_message("Tengo cucarachas"),
        conversation_history=[],
        business_context={"domain": "pest_control"},
    )

    response = await provider.process(request)

    assert provider.mode == "real"
    assert response.reply == "Respuesta desde provider HTTP."
    assert captured_payload["response_contract"] == "AgentResponse"
    assert captured_payload["message"]["channel"] == "telegram"
