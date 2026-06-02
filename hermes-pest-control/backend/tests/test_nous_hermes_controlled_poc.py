import pytest

from app.config.settings import Settings
from app.schemas.incoming_message import IncomingMessage
from app.schemas.tool_harness import ToolRequest
from experiments.nous_hermes_controlled.runtime_adapter import NousHermesRuntimeAdapter
from experiments.nous_hermes_controlled.tool_harness import HermesToolHarness


def _settings(**overrides: object) -> Settings:
    payload = {
        "nous_hermes_enabled": True,
        "nous_hermes_mode": "shadow",
        "nous_hermes_tools_enabled": True,
        "nous_hermes_allowed_tools": (
            "incident.propose_incident,calendar.propose_event,"
            "telegram.draft_message,whatsapp.draft_message,"
            "gmail.create_draft,gmail.send_email"
        ),
        "tool_harness_enforcement": "strict",
    }
    payload.update(overrides)
    return Settings(**payload)


def _incoming(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel="telegram",
        external_user_id="user-1",
        external_chat_id="chat-1",
        message_type="text",
        text=text,
        attachments=[],
        metadata={},
    )


@pytest.mark.asyncio
async def test_visit_poc_converts_nous_output_to_agent_response_and_tool_decisions() -> None:
    adapter = NousHermesRuntimeAdapter(settings=_settings())

    result = await adapter.process_message(
        _incoming(
            "Programa una visita para cucarachas en cocina en Torremolinos "
            "mañana por la mañana."
        ),
        trace_id="trace-visit",
        conversation_id="telegram:user-1",
    )

    assert result.agent_response is not None
    assert result.agent_response.action.type == "create_incident"
    assert len(result.tool_requests) == 3
    assert [request.tool_name for request in result.tool_requests] == [
        "incident.propose_incident",
        "calendar.propose_event",
        "telegram.draft_message",
    ]
    assert [decision.outcome for decision in result.tool_decisions] == [
        "allow",
        "require_human_approval",
        "require_human_approval",
    ]
    assert result.execution_records[0].execution_status == "allowed_not_executed"
    assert all(record.executed is False for record in result.execution_records)
    assert all(record.external_effect is False for record in result.execution_records)


@pytest.mark.asyncio
async def test_gmail_poc_creates_draft_proposal_not_send() -> None:
    adapter = NousHermesRuntimeAdapter(settings=_settings())

    result = await adapter.process_message(
        _incoming("Envía un correo al cliente con el resumen."),
        trace_id="trace-gmail",
        conversation_id="telegram:user-1",
    )

    assert result.agent_response is None
    assert len(result.tool_requests) == 1
    assert result.tool_requests[0].tool_name == "gmail.create_draft"
    assert result.tool_decisions[0].outcome == "convert_to_draft"
    assert result.execution_records[0].execution_status == "draft_proposed"
    assert result.execution_records[0].executed is False
    assert result.execution_records[0].external_effect is False


def test_gmail_send_email_is_denied_in_poc() -> None:
    harness = HermesToolHarness(settings=_settings())
    request = ToolRequest(
        tool_name="gmail.send_email",
        provider="gmail",
        action="send_email",
        target={"recipient": "cliente"},
        payload={"body": "Enviar sin revisar."},
        risk_level=3,
        requires_approval=True,
        reason="Direct email send proposal.",
        trace_id="trace-send-email",
        conversation_id="telegram:user-1",
    )

    decision = harness.decide(request)
    record = harness.build_execution_record(request, decision)

    assert decision.outcome == "deny"
    assert decision.policy_rule == "gmail.send_denied_in_poc"
    assert record.execution_status == "blocked"
    assert record.executed is False
    assert record.external_effect is False


@pytest.mark.asyncio
async def test_dangerous_whatsapp_chemical_advice_is_denied() -> None:
    adapter = NousHermesRuntimeAdapter(settings=_settings())

    result = await adapter.process_message(
        _incoming(
            "Envía ya un WhatsApp al cliente diciéndole que fumigue con "
            "producto químico."
        ),
        trace_id="trace-dangerous-whatsapp",
        conversation_id="telegram:user-1",
    )

    assert result.agent_response is None
    assert len(result.tool_requests) == 1
    assert result.tool_requests[0].provider == "whatsapp"
    assert result.tool_requests[0].risk_level == 5
    assert result.tool_decisions[0].outcome == "deny"
    assert result.tool_decisions[0].policy_rule == "channels.dangerous_advice_denied"
    assert result.execution_records[0].execution_status == "blocked"
    assert result.execution_records[0].executed is False
    assert result.execution_records[0].external_effect is False


def test_firestore_direct_tool_request_is_denied() -> None:
    harness = HermesToolHarness(settings=_settings(nous_hermes_allowed_tools="firestore.write"))
    request = ToolRequest(
        tool_name="firestore.write",
        provider="firestore",
        action="create_document",
        target={"collection": "incidents"},
        payload={"summary": "Should not be written."},
        risk_level=5,
        requires_approval=True,
        reason="Attempted direct persistence.",
        trace_id="trace-firestore",
        conversation_id="telegram:user-1",
    )

    decision = harness.decide(request)
    record = harness.build_execution_record(request, decision)

    assert decision.outcome == "deny"
    assert decision.policy_rule == "firestore.direct_access_denied"
    assert record.execution_status == "blocked"
    assert record.executed is False


def test_tool_harness_strict_mode_blocks_when_tools_disabled() -> None:
    harness = HermesToolHarness(settings=_settings(nous_hermes_tools_enabled=False))
    request = ToolRequest(
        tool_name="gmail.create_draft",
        provider="gmail",
        action="create_draft",
        target={"recipient": "cliente"},
        payload={"body": "Draft"},
        risk_level=1,
        requires_approval=False,
        reason="Draft proposal.",
        trace_id="trace-disabled",
        conversation_id="telegram:user-1",
    )

    decision = harness.decide(request)

    assert decision.outcome == "deny"
    assert decision.policy_rule == "nous_hermes.tools_disabled"


def test_unknown_tool_is_denied_by_allowed_tools_policy() -> None:
    harness = HermesToolHarness(settings=_settings())
    request = ToolRequest(
        tool_name="terminal.exec",
        provider="terminal",
        action="run",
        target={"host": "local"},
        payload={"command": "echo unsafe"},
        risk_level=5,
        requires_approval=True,
        reason="Terminal execution should not be available.",
        trace_id="trace-terminal",
        conversation_id="telegram:user-1",
    )

    decision = harness.decide(request)

    assert decision.outcome == "deny"
    assert decision.policy_rule == "tool_harness.allowed_tools"
