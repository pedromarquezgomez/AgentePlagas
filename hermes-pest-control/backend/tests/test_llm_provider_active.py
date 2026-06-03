import json

import httpx
import pytest

from app.config.settings import Settings
from app.context.contracts import ConversationContext
from app.harness.providers.llm_provider import LLMRuntimeProvider
from app.policies.contracts import PolicyContext, PolicyDecision
from app.policies.engine import PolicyEngine
from app.schemas.incoming_message import IncomingMessage
from app.services.conversation_service import ConversationService
from app.services.hermes_service import HermesService
from app.services.mock_firestore_service import MockFirestoreService
from app.skills.registry import default_skill_registry
from app.tools.registry import default_tool_registry


def _incoming_message(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel="telegram",
        external_user_id="llm-user",
        external_chat_id="llm-chat",
        message_type="text",
        text=text,
        attachments=[],
        metadata={},
    )


def _context(text: str) -> ConversationContext:
    message = _incoming_message(text)
    policy_engine = PolicyEngine()
    return ConversationContext(
        message=message,
        channel=message.channel,
        user_id=message.external_user_id,
        conversation_id=f"{message.channel}:{message.external_user_id}",
        history=[],
        available_skills=default_skill_registry().list_skills(),
        available_tools=default_tool_registry().list_tools(),
        policy_constraints=policy_engine.get_constraints(),
        metadata={"trace_id": "trace-llm-active"},
    )


def _settings() -> Settings:
    return Settings(
        app_env="test",
        agent_provider="llm",
        llm_provider="openai",
        llm_api_key="test-llm-key",
        llm_model="gpt-test",
        llm_timeout_seconds=20,
        llm_fallback_provider="mock",
        llm_active_mode="pilot",
        hermes_shadow_mode=False,
    )


def _llm_response(payload: dict) -> dict:
    return {"output_text": json.dumps(payload)}


@pytest.mark.asyncio
async def test_llm_provider_returns_valid_json_response() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.read())
        return httpx.Response(
            200,
            json=_llm_response(
                {
                    "reply": "Te ayudo a registrar el aviso. ¿Me indicas la localidad?",
                    "action": {
                        "type": "collect_missing_data",
                        "missing_fields": ["location", "customer_name"],
                    },
                    "incident": {"should_create": False},
                    "metadata": {},
                }
            ),
        )

    provider = LLMRuntimeProvider(_settings(), transport=httpx.MockTransport(handler))

    response = await provider.process(_context("Tengo hormigas en casa"))

    assert response.action.type == "collect_missing_data"
    assert response.action.missing_fields == ["location", "customer_name"]
    assert captured_payload["model"] == "gpt-test"
    assert "Policy Constraints" in captured_payload["input"][1]["content"]
    assert "create_incident_tool" in captured_payload["input"][1]["content"]


@pytest.mark.asyncio
async def test_llm_provider_can_propose_create_incident() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_llm_response(
                {
                    "reply": (
                        "Gracias, he registrado el aviso para que el equipo lo revise."
                    ),
                    "action": {"type": "create_incident", "missing_fields": []},
                    "incident": {
                        "should_create": True,
                        "pest_type": "cucarachas",
                        "location": "Torremolinos",
                        "affected_area": "cocina",
                        "priority": "high",
                        "summary": (
                            "Cliente informa de cucarachas en cocina en Torremolinos."
                        ),
                    },
                    "metadata": {},
                }
            ),
        )

    provider = LLMRuntimeProvider(_settings(), transport=httpx.MockTransport(handler))

    response = await provider.process(
        _context(
            "Tengo cucarachas en la cocina de Torremolinos. Mi nombre es Pedro."
        )
    )

    assert response.action.type == "create_incident"
    assert response.incident is not None
    assert response.incident.should_create is True
    assert response.incident.pest_type == "cucarachas"


@pytest.mark.asyncio
async def test_llm_timeout_falls_back_to_mock_provider() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=request)

    provider = LLMRuntimeProvider(_settings(), transport=httpx.MockTransport(handler))

    response = await provider.process(
        _context("Tengo cucarachas en la cocina en Torremolinos desde hace una semana")
    )

    assert response.action.type == "create_incident"
    assert response.metadata["fallback_used"] is True
    assert response.metadata["fallback_reason"] == "LLMProviderError:timeout"
    assert response.metadata["fallback_provider"] == "mock"


@pytest.mark.asyncio
async def test_llm_invalid_json_falls_back_to_mock_provider() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output_text": "not-json"})

    provider = LLMRuntimeProvider(_settings(), transport=httpx.MockTransport(handler))

    response = await provider.process(
        _context("Tengo cucarachas en la cocina en Torremolinos desde hace una semana")
    )

    assert response.action.type == "create_incident"
    assert response.metadata["fallback_used"] is True
    assert response.metadata["fallback_reason"] == "LLMProviderError:invalid_response"


def test_llm_proposed_unknown_tool_is_blocked_by_policy_engine() -> None:
    decision = PolicyEngine().evaluate(
        PolicyContext(
            channel="telegram",
            user_id="llm-user",
            requested_tool="close_incident_tool",
            requested_action="close_incident",
            source_provider="llm_provider",
        )
    )

    assert decision.decision == PolicyDecision.DENY
    assert decision.policy_rule == "default.deny_unknown_tool"


@pytest.mark.asyncio
async def test_llm_with_incomplete_data_requests_missing_information() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_llm_response(
                {
                    "reply": (
                        "Para ayudarte necesito saber en qué localidad ocurre y "
                        "un nombre de contacto."
                    ),
                    "action": {
                        "type": "collect_missing_data",
                        "missing_fields": ["location", "customer_name"],
                    },
                    "incident": {"should_create": False},
                    "metadata": {},
                }
            ),
        )

    provider = LLMRuntimeProvider(_settings(), transport=httpx.MockTransport(handler))

    response = await provider.process(_context("Tengo hormigas en casa"))

    assert response.action.type == "collect_missing_data"
    assert response.incident is not None
    assert response.incident.should_create is False


@pytest.mark.asyncio
async def test_conversation_service_uses_llm_provider_as_primary_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_llm_response(
                {
                    "reply": "Respuesta del LLM principal sin ejecutar herramientas.",
                    "action": {
                        "type": "collect_missing_data",
                        "missing_fields": ["affected_area", "customer_name"],
                    },
                    "incident": {"should_create": False},
                    "metadata": {},
                }
            ),
        )

    settings = _settings()
    provider = LLMRuntimeProvider(settings, transport=httpx.MockTransport(handler))
    hermes_service = HermesService(settings=settings, provider=provider)
    firestore_service = MockFirestoreService()
    conversation_service = ConversationService(
        hermes_service=hermes_service,
        firestore_service=firestore_service,
        settings=settings,
    )

    response = await conversation_service.handle_incoming_message(
        _incoming_message("Tengo unos bichos raros")
    )

    assert response.reply == "Respuesta del LLM principal sin ejecutar herramientas."
    assert response.action.type == "collect_missing_data"
    assert response.metadata.get("fallback_used") is not True
