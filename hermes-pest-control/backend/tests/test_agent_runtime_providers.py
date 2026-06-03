import json

import httpx
import pytest

from app.config.settings import Settings
from app.context.contracts import ConversationContext
from app.harness.providers.hermes_http_provider import HermesHttpRuntimeProvider
from app.harness.providers.llm_provider import LLMRuntimeProvider
from app.harness.providers.mock_provider import MockAgentRuntimeProvider
from app.schemas.incoming_message import IncomingMessage
from app.skills.registry import default_skill_registry
from app.tools.registry import default_tool_registry


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
    message = _incoming_message("Tengo cucarachas en la cocina en Torremolinos")
    context = ConversationContext(
        message=message,
        channel=message.channel,
        user_id=message.external_user_id,
        conversation_id=f"{message.channel}:{message.external_user_id}",
        metadata={"conversation_id": "telegram:runtime-user"},
    )

    response = await provider.process(context)

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
    
    message = _incoming_message("Tengo cucarachas")
    context = ConversationContext(
        message=message,
        channel=message.channel,
        user_id=message.external_user_id,
        conversation_id=f"{message.channel}:{message.external_user_id}",
        history=[],
        metadata={"domain": "pest_control"},
        available_skills=default_skill_registry().list_skills(),
        available_tools=default_tool_registry().list_tools(),
    )

    response = await provider.process(context)

    assert provider.mode == "nous_hermes"
    assert response.reply == "Respuesta desde provider HTTP."
    assert captured_payload["response_contract"] == "AgentResponse"
    assert captured_payload["message"]["channel"] == "telegram"
    assert captured_payload["available_skills"][0]["name"] == "classify_pest"
    assert captured_payload["available_tools"][0]["name"] == "create_incident_tool"


@pytest.mark.asyncio
async def test_llm_runtime_provider_returns_valid_agent_response() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.read())
        return httpx.Response(
            200,
            json={
                "output_text": json.dumps(
                    {
                        "reply": "Respuesta desde LLM.",
                        "action": {
                            "type": "collect_missing_data",
                            "missing_fields": ["location"],
                        },
                        "incident": {"should_create": False},
                        "metadata": {},
                    }
                )
            },
        )

    provider = LLMRuntimeProvider(
        Settings(
            agent_provider="llm",
            llm_provider="openai",
            llm_api_key="test-openai-key",
            llm_model="gpt-test",
            openai_api_key="test-openai-key",
            openai_model="gpt-test",
        ),
        transport=httpx.MockTransport(handler),
    )
    
    message = _incoming_message("Tengo cucarachas")
    context = ConversationContext(
        message=message,
        channel=message.channel,
        user_id=message.external_user_id,
        conversation_id=f"{message.channel}:{message.external_user_id}",
        history=[],
        metadata={"trace_id": "trace-runtime"},
        available_skills=default_skill_registry().list_skills(),
        available_tools=default_tool_registry().list_tools(),
    )

    response = await provider.process(context)

    assert provider.mode == "llm"
    assert response.reply == "Respuesta desde LLM."
    assert response.action.type == "collect_missing_data"
    assert captured_payload["model"] == "gpt-test"
    assert captured_payload["text"]["format"]["name"] == "AgentResponse"
    assert "classify_pest" in captured_payload["input"][1]["content"]
    assert "create_incident_tool" in captured_payload["input"][1]["content"]


@pytest.mark.asyncio
async def test_llm_runtime_provider_falls_back_to_mock_on_invalid_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output_text": "not-json"})

    provider = LLMRuntimeProvider(
        Settings(
            agent_provider="llm",
            llm_provider="openai",
            openai_api_key="test-openai-key",
            openai_model="gpt-test",
        ),
        transport=httpx.MockTransport(handler),
    )

    message = _incoming_message("Tengo cucarachas")
    context = ConversationContext(
        message=message,
        channel=message.channel,
        user_id=message.external_user_id,
        conversation_id=f"{message.channel}:{message.external_user_id}",
    )

    response = await provider.process(context)

    assert response.action.type == "collect_missing_data"
    assert response.metadata["fallback_used"] is True
    assert response.metadata["fallback_reason"] == "LLMProviderError:invalid_response"
    assert response.metadata["fallback_provider"] == "mock"
