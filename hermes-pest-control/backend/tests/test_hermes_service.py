import json

import httpx
import pytest

from app.config.settings import Settings
from app.schemas.incoming_message import IncomingMessage
from app.services.hermes_clients import HermesClientError, HermesRealClient
from app.services.hermes_service import HermesService


def _incoming_message(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel="telegram",
        external_user_id="test-user-1",
        external_chat_id="test-chat-1",
        message_type="text",
        text=text,
        attachments=[],
        metadata={},
    )


@pytest.mark.asyncio
async def test_hermes_mode_mock_keeps_create_incident_behavior() -> None:
    service = HermesService(Settings(hermes_mode="mock"))

    response = await service.process_message(
        _incoming_message(
            "Tengo cucarachas en la cocina en Torremolinos desde hace una semana"
        ),
        "telegram:test-user-1",
    )

    assert response.action.type == "create_incident"
    assert response.incident is not None
    assert response.incident.should_create is True
    assert response.incident.pest_type == "cucarachas"


@pytest.mark.asyncio
async def test_hermes_mode_mock_keeps_collect_missing_data_behavior() -> None:
    service = HermesService(Settings(hermes_mode="mock"))

    response = await service.process_message(
        _incoming_message("Tengo cucarachas"),
        "telegram:test-user-1",
    )

    assert response.action.type == "collect_missing_data"
    assert response.action.missing_fields == ["affected_area", "location"]
    assert response.incident is not None
    assert response.incident.should_create is False


@pytest.mark.asyncio
async def test_hermes_mode_real_returns_valid_agent_response_from_http_client() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.read())
        return httpx.Response(
            200,
            json={
                "reply": "Respuesta real validada.",
                "action": {"type": "collect_missing_data", "missing_fields": ["location"]},
                "incident": {"should_create": False},
            },
        )

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/process",
        hermes_api_key="test-key",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))
    service = HermesService(settings, client=client)

    response = await service.process_message(
        _incoming_message("Tengo cucarachas"),
        conversation_history=[],
        business_context={"domain": "pest_control"},
    )

    assert response.reply == "Respuesta real validada."
    assert response.action.type == "collect_missing_data"
    assert captured_payload["response_contract"] == "AgentResponse"
    assert captured_payload["business_context"]["domain"] == "pest_control"
    assert captured_payload["message"]["channel"] == "telegram"


@pytest.mark.asyncio
async def test_hermes_real_client_sends_shadow_agent_key_header() -> None:
    captured_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = dict(request.headers)
        return httpx.Response(
            200,
            json={
                "reply": "Respuesta shadow validada.",
                "action": {"type": "create_incident", "missing_fields": []},
                "incident": {
                    "should_create": True,
                    "pest_type": "cucarachas",
                    "location": "Torremolinos",
                    "affected_area": "cocina",
                    "priority": "high",
                    "summary": "Shadow test.",
                },
            },
        )

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/agent",
        hermes_shadow_api_key="shadow-agent-key",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))

    response = await client.process_message(_incoming_message("Tengo cucarachas"))

    assert response.action.type == "create_incident"
    assert captured_headers["x-hermes-agent-key"] == "shadow-agent-key"


@pytest.mark.asyncio
async def test_hermes_real_client_strips_shadow_agent_key_header() -> None:
    captured_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = dict(request.headers)
        return httpx.Response(
            200,
            json={
                "reply": "Respuesta shadow validada.",
                "action": {"type": "collect_missing_data", "missing_fields": ["location"]},
                "incident": {"should_create": False},
            },
        )

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/agent",
        hermes_shadow_api_key="shadow-agent-key\n",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))

    response = await client.process_message(_incoming_message("Tengo cucarachas"))

    assert response.action.type == "collect_missing_data"
    assert captured_headers["x-hermes-agent-key"] == "shadow-agent-key"


@pytest.mark.asyncio
async def test_hermes_real_client_sends_trace_id_header() -> None:
    captured_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = dict(request.headers)
        return httpx.Response(
            200,
            json={
                "reply": "Respuesta shadow validada.",
                "action": {"type": "collect_missing_data", "missing_fields": ["location"]},
                "incident": {"should_create": False},
            },
        )

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/agent",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))

    response = await client.process_message(
        _incoming_message("Tengo cucarachas"),
        business_context={"trace_id": "trace-123"},
    )

    assert response.action.type == "collect_missing_data"
    assert captured_headers["x-hermes-trace-id"] == "trace-123"


@pytest.mark.asyncio
async def test_hermes_real_client_invalid_json_raises_controlled_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/process",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))

    with pytest.raises(HermesClientError, match="invalid JSON") as exc_info:
        await client.process_message(_incoming_message("Tengo cucarachas"))
    assert exc_info.value.normalized_error == "HermesClientError:invalid_json"


@pytest.mark.asyncio
async def test_hermes_real_client_invalid_agent_response_raises_controlled_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"reply": "missing action"})

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/process",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))

    with pytest.raises(HermesClientError, match="response contract") as exc_info:
        await client.process_message(_incoming_message("Tengo cucarachas"))
    assert exc_info.value.normalized_error == "HermesClientError:invalid_contract"


@pytest.mark.asyncio
async def test_hermes_real_client_timeout_raises_controlled_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=request)

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/process",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))

    with pytest.raises(HermesClientError, match="timed out") as exc_info:
        await client.process_message(_incoming_message("Tengo cucarachas"))
    assert exc_info.value.normalized_error == "HermesClientError:timeout"


@pytest.mark.asyncio
async def test_hermes_real_client_connect_error_raises_normalized_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/process",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))

    with pytest.raises(HermesClientError, match="connection failed") as exc_info:
        await client.process_message(_incoming_message("Tengo cucarachas"))
    assert exc_info.value.normalized_error == "HermesClientError:connection_error"


@pytest.mark.asyncio
async def test_hermes_real_client_http_error_raises_controlled_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/process",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))

    with pytest.raises(HermesClientError, match="HTTP 500") as exc_info:
        await client.process_message(_incoming_message("Tengo cucarachas"))
    assert exc_info.value.normalized_error == "HermesClientError:http_500"


@pytest.mark.asyncio
async def test_hermes_real_client_http_401_raises_normalized_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Unauthorized"})

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/process",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))

    with pytest.raises(HermesClientError, match="HTTP 401") as exc_info:
        await client.process_message(_incoming_message("Tengo cucarachas"))
    assert exc_info.value.normalized_error == "HermesClientError:http_401"


@pytest.mark.asyncio
async def test_hermes_mode_real_invalid_response_uses_safe_fallback() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/process",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))
    service = HermesService(settings, client=client)

    response = await service.process_message(_incoming_message("Tengo cucarachas"))

    assert response.action.type == "escalate_to_human"
    assert response.incident is not None
    assert response.incident.should_create is True
    assert response.incident.priority == "medium"


@pytest.mark.asyncio
async def test_hermes_mode_real_timeout_uses_safe_fallback() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=request)

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/process",
        hermes_timeout_seconds=0.01,
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))
    service = HermesService(settings, client=client)

    response = await service.process_message(_incoming_message("Tengo cucarachas"))

    assert response.action.type == "escalate_to_human"
    assert response.reply.startswith("Ahora mismo no he podido procesar")
    assert response.metadata["fallback_reason"] == "HermesClientError:timeout"


@pytest.mark.asyncio
async def test_hermes_mode_real_http_error_uses_safe_fallback() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"detail": "Agent output invalid."})

    settings = Settings(
        hermes_mode="real",
        hermes_api_url="https://hermes-agent.test/process",
    )
    client = HermesRealClient(settings, transport=httpx.MockTransport(handler))
    service = HermesService(settings, client=client)

    response = await service.process_message(_incoming_message("Tengo cucarachas"))

    assert response.action.type == "escalate_to_human"
    assert response.incident is not None
    assert response.incident.should_create is True
    assert response.metadata["fallback_used"] is True
    assert response.metadata["fallback_reason"] == "HermesClientError:http_502"
