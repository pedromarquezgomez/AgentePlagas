"""
Tests unitarios del LLMRuntimeProvider.

Todos los tests usan httpx.MockTransport para evitar llamadas reales a OpenAI.
Verifican que el proveedor LLM:
  - Parsea correctamente respuestas válidas como AgentResponse
  - Aplica fallback al mock ante cualquier error de red o respuesta inválida
  - Nunca ejecuta tools directamente (solo propone acciones)
  - Registra el motivo del fallback en metadata
"""
import json
from typing import Generator

import httpx
import pytest

from app.config.settings import Settings
from app.context.contracts import ConversationContext
from app.schemas.incoming_message import IncomingMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(text: str = "Tengo cucarachas en la cocina de mi restaurante. Mi nombre es Pedro.") -> ConversationContext:
    message = IncomingMessage(
        channel="telegram",
        external_user_id="llm-test-user",
        external_chat_id="llm-test-chat",
        message_type="text",
        text=text,
        attachments=[],
        metadata={},
    )
    return ConversationContext(
        message=message,
        channel="telegram",
        user_id="llm-test-user",
        conversation_id="telegram:llm-test-user",
        metadata={"trace_id": "trace-llm-test"},
    )


def _valid_llm_response_body(reply: str = "He registrado tu aviso.") -> bytes:
    """Simula la estructura de respuesta de OpenAI /v1/responses."""
    payload = {
        "output": [
            {
                "content": [
                    {
                        "text": json.dumps({
                            "reply": reply,
                            "action": {
                                "type": "create_incident",
                                "missing_fields": [],
                            },
                            "incident": {
                                "should_create": True,
                                "pest_type": "COCKROACH",
                                "location": "restaurante",
                                "affected_area": "cocina",
                                "priority": "urgent",
                                "summary": "Cucarachas en cocina de restaurante.",
                                "id": None,
                                "conversation_id": None,
                                "status": None,
                            },
                            "metadata": {},
                        })
                    }
                ]
            }
        ]
    }
    return json.dumps(payload).encode()


def _settings_with_key(model: str = "gpt-4.1-mini") -> Settings:
    return Settings(
        agent_provider="llm",
        llm_provider="openai",
        llm_api_key="sk-test-fake-key",
        llm_model=model,
        llm_timeout_seconds=5.0,
        llm_fallback_provider="mock",
    )


# ---------------------------------------------------------------------------
# Tests de respuesta válida
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_provider_valid_response_returns_agent_response() -> None:
    """Cuando el LLM devuelve JSON válido, el proveedor lo convierte a AgentResponse."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=_valid_llm_response_body())
    )
    provider = LLMRuntimeProvider(settings=_settings_with_key(), transport=transport)
    context = _make_context()

    response = await provider.process(context)

    assert response.reply == "He registrado tu aviso."
    assert response.action.type == "create_incident"
    assert response.incident is not None
    assert response.incident.should_create is True
    assert response.incident.pest_type == "COCKROACH"
    # El LLM solo propone — no marca fallback_used
    assert not response.metadata.get("fallback_used", False)


@pytest.mark.asyncio
async def test_llm_provider_valid_response_does_not_execute_tools() -> None:
    """El proveedor LLM solo propone acciones, nunca ejecuta tools directamente."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=_valid_llm_response_body())
    )
    provider = LLMRuntimeProvider(settings=_settings_with_key(), transport=transport)
    context = _make_context()

    response = await provider.process(context)

    # La respuesta es una propuesta, no una ejecución
    assert response.action.type in {"create_incident", "collect_missing_data",
                                     "escalate_to_human", "reply_only"}
    # metadata no indica ejecución directa
    assert "tool_executed" not in response.metadata


# ---------------------------------------------------------------------------
# Tests de fallback por errores de red
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_provider_timeout_falls_back_to_mock() -> None:
    """Un timeout de red activa el fallback al mock con motivo registrado."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    def _timeout_transport(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Timeout", request=request)

    provider = LLMRuntimeProvider(
        settings=_settings_with_key(),
        transport=httpx.MockTransport(_timeout_transport),
    )
    context = _make_context()

    response = await provider.process(context)

    assert response.metadata.get("fallback_used") is True
    assert response.metadata.get("fallback_provider") == "mock"
    assert response.metadata.get("llm_provider_failed") is True
    assert "timeout" in response.metadata.get("fallback_reason", "").casefold()


@pytest.mark.asyncio
async def test_llm_provider_http_error_falls_back_to_mock() -> None:
    """Un error genérico de HTTP activa el fallback al mock."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    def _http_error_transport(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    provider = LLMRuntimeProvider(
        settings=_settings_with_key(),
        transport=httpx.MockTransport(_http_error_transport),
    )
    context = _make_context()

    response = await provider.process(context)

    assert response.metadata.get("fallback_used") is True
    assert "request_failed" in response.metadata.get("fallback_reason", "")


@pytest.mark.asyncio
async def test_llm_provider_http_401_falls_back_to_mock() -> None:
    """HTTP 401 (credenciales inválidas) activa el fallback al mock."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, content=b'{"error": "invalid_api_key"}')
    )
    provider = LLMRuntimeProvider(settings=_settings_with_key(), transport=transport)
    context = _make_context()

    response = await provider.process(context)

    assert response.metadata.get("fallback_used") is True
    assert "401" in response.metadata.get("fallback_reason", "")


@pytest.mark.asyncio
async def test_llm_provider_http_429_falls_back_to_mock() -> None:
    """HTTP 429 (rate limit) activa el fallback al mock."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    transport = httpx.MockTransport(
        lambda request: httpx.Response(429, content=b'{"error": "rate_limit_exceeded"}')
    )
    provider = LLMRuntimeProvider(settings=_settings_with_key(), transport=transport)
    context = _make_context()

    response = await provider.process(context)

    assert response.metadata.get("fallback_used") is True
    assert "429" in response.metadata.get("fallback_reason", "")


# ---------------------------------------------------------------------------
# Tests de fallback por respuesta inválida
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_provider_invalid_json_falls_back_to_mock() -> None:
    """Si el LLM devuelve JSON que no cumple AgentResponse, se activa el fallback."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    bad_body = json.dumps({
        "output": [{"content": [{"text": "esto no es JSON válido para AgentResponse"}]}]
    }).encode()

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=bad_body)
    )
    provider = LLMRuntimeProvider(settings=_settings_with_key(), transport=transport)
    context = _make_context()

    response = await provider.process(context)

    assert response.metadata.get("fallback_used") is True
    assert "invalid_response" in response.metadata.get("fallback_reason", "")


@pytest.mark.asyncio
async def test_llm_provider_empty_output_falls_back_to_mock() -> None:
    """Si el LLM devuelve output vacío, se activa el fallback."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    bad_body = json.dumps({"output": []}).encode()

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=bad_body)
    )
    provider = LLMRuntimeProvider(settings=_settings_with_key(), transport=transport)
    context = _make_context()

    response = await provider.process(context)

    assert response.metadata.get("fallback_used") is True


# ---------------------------------------------------------------------------
# Tests de configuración incorrecta
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_provider_no_api_key_falls_back_immediately() -> None:
    """Sin API key, el proveedor hace fallback inmediato sin llamar a la API."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    settings = Settings(
        agent_provider="llm",
        llm_provider="openai",
        llm_api_key="",
        openai_api_key="",
        llm_model="gpt-4.1-mini",
        llm_fallback_provider="mock",
    )

    calls: list[str] = []

    def _should_not_be_called(request: httpx.Request) -> httpx.Response:
        calls.append("called")
        return httpx.Response(200, content=b"{}")

    provider = LLMRuntimeProvider(
        settings=settings,
        transport=httpx.MockTransport(_should_not_be_called),
    )
    context = _make_context()

    response = await provider.process(context)

    assert response.metadata.get("fallback_used") is True
    assert "not_configured" in response.metadata.get("fallback_reason", "")
    # Nunca debería haber llamado a la API
    assert calls == []


@pytest.mark.asyncio
async def test_llm_provider_no_model_falls_back_immediately() -> None:
    """Sin modelo configurado, el proveedor hace fallback inmediato."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    settings = Settings(
        agent_provider="llm",
        llm_provider="openai",
        llm_api_key="sk-test-fake-key",
        llm_model="",
        openai_model="",
        llm_fallback_provider="mock",
    )

    calls: list[str] = []

    def _should_not_be_called(request: httpx.Request) -> httpx.Response:
        calls.append("called")
        return httpx.Response(200, content=b"{}")

    provider = LLMRuntimeProvider(
        settings=settings,
        transport=httpx.MockTransport(_should_not_be_called),
    )
    context = _make_context()

    response = await provider.process(context)

    assert response.metadata.get("fallback_used") is True
    assert "model_not_configured" in response.metadata.get("fallback_reason", "")
    assert calls == []


@pytest.mark.asyncio
async def test_llm_provider_unsupported_provider_falls_back_immediately() -> None:
    """Con un proveedor LLM no soportado, hace fallback sin llamar a la API."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    settings = Settings(
        agent_provider="llm",
        llm_provider="anthropic",  # No soportado todavía
        llm_api_key="sk-ant-fake",
        llm_model="claude-3-sonnet",
        llm_fallback_provider="mock",
    )

    calls: list[str] = []

    def _should_not_be_called(request: httpx.Request) -> httpx.Response:
        calls.append("called")
        return httpx.Response(200, content=b"{}")

    provider = LLMRuntimeProvider(
        settings=settings,
        transport=httpx.MockTransport(_should_not_be_called),
    )
    context = _make_context()

    response = await provider.process(context)

    assert response.metadata.get("fallback_used") is True
    assert "unsupported_provider" in response.metadata.get("fallback_reason", "")
    assert calls == []


# ---------------------------------------------------------------------------
# Test de integración: el mock siempre produce una respuesta válida como fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_fallback_mock_always_returns_valid_agent_response() -> None:
    """El fallback al mock siempre devuelve un AgentResponse estructuralmente válido."""
    from app.harness.providers.llm_provider import LLMRuntimeProvider

    settings = Settings(
        agent_provider="llm",
        llm_provider="openai",
        llm_api_key="",  # Sin key → fallback inmediato
        openai_api_key="",
        llm_model="gpt-4.1-mini",
        llm_fallback_provider="mock",
    )
    provider = LLMRuntimeProvider(settings=settings)
    context = _make_context()

    response = await provider.process(context)

    # La respuesta del mock debe ser un AgentResponse válido
    assert isinstance(response.reply, str)
    assert len(response.reply) > 0
    assert response.action.type in {
        "reply_only", "create_incident", "collect_missing_data", "escalate_to_human"
    }
    assert response.metadata.get("fallback_used") is True
    assert response.metadata.get("effective_agent_provider") == "mock"
