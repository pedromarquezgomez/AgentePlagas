from pathlib import Path
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings
from scripts import hermes_agent_server


def _payload(text: str) -> dict:
    return {
        "message": {
            "channel": "telegram",
            "external_user_id": "agent-test-user",
            "external_chat_id": "agent-test-chat",
            "message_type": "text",
            "text": text,
            "attachments": [],
            "metadata": {},
        },
        "conversation_history": [],
        "business_context": {"domain": "pest_control"},
        "response_contract": "AgentResponse",
    }


def test_load_skills_prompt_uses_required_skill_files() -> None:
    skills_dir = Path(__file__).resolve().parents[2] / "hermes" / "skills"

    prompt = hermes_agent_server.load_skills_prompt(str(skills_dir))

    assert "02 Pest Control Domain" in prompt
    assert "05 Agent Response Contract" in prompt
    assert "08 Safety And Compliance" in prompt


def test_extract_json_object_from_fenced_agent_text() -> None:
    raw_output = """
    Claro. La salida estructurada es:

    ```json
    {
      "reply": "Necesito la localidad.",
      "action": {"type": "collect_missing_data", "missing_fields": ["location"]},
      "incident": {"should_create": false}
    }
    ```
    """

    response = hermes_agent_server.parse_agent_output(raw_output)

    assert response.action.type == "collect_missing_data"
    assert response.action.missing_fields == ["location"]


def test_process_agent_request_returns_valid_agent_response() -> None:
    skills_dir = Path(__file__).resolve().parents[2] / "hermes" / "skills"
    settings = Settings(hermes_agent_mode="local", hermes_skills_dir=str(skills_dir))

    response = hermes_agent_server.process_agent_request(
        _payload("Tengo cucarachas en la cocina en Torremolinos"),
        settings,
    )

    assert response.action.type == "create_incident"
    assert response.incident is not None
    assert response.incident.should_create is True
    assert response.incident.location == "Torremolinos"


def test_llm_agent_mode_with_mock_openai_response_returns_valid_agent_response() -> None:
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = json.loads(request.read())
        assert request.headers["Authorization"] == "Bearer test-openai-key"
        return httpx.Response(
            200,
            json={
                "output_text": json.dumps(
                    {
                        "reply": "Necesito la localidad.",
                        "action": {
                            "type": "collect_missing_data",
                            "missing_fields": ["location"],
                        },
                        "incident": {"should_create": False},
                    }
                )
            },
        )

    settings = Settings(
        hermes_agent_mode="llm",
        llm_provider="openai",
        openai_api_key="test-openai-key",
        openai_model="test-model",
    )

    raw_output = hermes_agent_server.run_llm_agent(
        "Return AgentResponse JSON.",
        settings,
        transport=httpx.MockTransport(handler),
    )
    response = hermes_agent_server.parse_agent_output(raw_output)

    assert response.action.type == "collect_missing_data"
    assert response.action.missing_fields == ["location"]
    assert captured_request["model"] == "test-model"
    assert captured_request["text"]["format"]["type"] == "json_schema"
    assert captured_request["text"]["format"]["strict"] is True
    assert captured_request["temperature"] == 0


def test_llm_agent_mode_invalid_output_raises_controlled_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output_text": "not structured json"})

    settings = Settings(
        hermes_agent_mode="llm",
        llm_provider="openai",
        openai_api_key="test-openai-key",
        openai_model="test-model",
    )

    raw_output = hermes_agent_server.run_llm_agent(
        "Return AgentResponse JSON.",
        settings,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(hermes_agent_server.HermesAgentServerError):
        hermes_agent_server.parse_agent_output(raw_output)


def test_llm_agent_mode_requires_openai_configuration() -> None:
    settings = Settings(hermes_agent_mode="llm", llm_provider="openai")

    with pytest.raises(hermes_agent_server.HermesAgentConfigurationError):
        hermes_agent_server.run_llm_agent("Return AgentResponse JSON.", settings)


def test_process_agent_request_rejects_wrong_response_contract() -> None:
    with pytest.raises(hermes_agent_server.HermesAgentServerError):
        hermes_agent_server.process_agent_request(
            {
                **_payload("Tengo cucarachas"),
                "response_contract": "OtherContract",
            }
        )


def test_agent_endpoint_returns_502_for_invalid_runtime_output(monkeypatch) -> None:
    def invalid_agent_output(*_args, **_kwargs) -> str:
        return "no structured json here"

    monkeypatch.setattr(hermes_agent_server, "run_agent", invalid_agent_output)
    client = TestClient(hermes_agent_server.app)

    response = client.post("/agent", json=_payload("Tengo cucarachas"))

    assert response.status_code == 502
    assert "valid JSON" in response.json()["detail"]


def test_agent_endpoint_requires_api_key_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(hermes_agent_server.settings, "hermes_agent_api_key", "agent-key")
    client = TestClient(hermes_agent_server.app)

    response = client.post("/agent", json=_payload("Tengo cucarachas"))

    assert response.status_code == 401
    assert "agent-key" not in response.text


def test_agent_endpoint_accepts_api_key_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(hermes_agent_server.settings, "hermes_agent_api_key", "agent-key")
    monkeypatch.setattr(hermes_agent_server.settings, "hermes_agent_mode", "local")
    client = TestClient(hermes_agent_server.app)

    response = client.post(
        "/agent",
        json=_payload("Tengo cucarachas en la cocina en Torremolinos"),
        headers={"X-Hermes-Agent-Key": "agent-key"},
    )

    assert response.status_code == 200
    assert response.json()["action"]["type"] == "create_incident"


def test_agent_endpoint_propagates_trace_id_to_processor(monkeypatch) -> None:
    captured_trace_id = None

    def fake_process_agent_request(payload, runtime_settings=None, trace_id=None):
        nonlocal captured_trace_id
        captured_trace_id = trace_id
        return hermes_agent_server.AgentResponse.model_validate(
            {
                "reply": "Respuesta trazada.",
                "action": {"type": "collect_missing_data", "missing_fields": ["location"]},
                "incident": {"should_create": False},
            }
        )

    monkeypatch.setattr(hermes_agent_server.settings, "hermes_agent_api_key", "")
    monkeypatch.setattr(
        hermes_agent_server,
        "process_agent_request",
        fake_process_agent_request,
    )
    client = TestClient(hermes_agent_server.app)

    response = client.post(
        "/agent",
        json=_payload("Tengo cucarachas"),
        headers={"X-Hermes-Trace-Id": "trace-wrapper-123"},
    )

    assert response.status_code == 200
    assert captured_trace_id == "trace-wrapper-123"
