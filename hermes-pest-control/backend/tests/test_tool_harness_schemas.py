import pytest
from pydantic import ValidationError

from app.schemas.tool_harness import ToolDecision, ToolExecutionRecord, ToolRequest


def _tool_request(**overrides: object) -> ToolRequest:
    payload = {
        "tool_name": "gmail.create_draft",
        "provider": "gmail",
        "action": "create_draft",
        "target": {"recipient": "cliente"},
        "payload": {"subject": "Resumen"},
        "risk_level": 1,
        "requires_approval": False,
        "reason": "Crear borrador para revisión.",
        "trace_id": "trace-1",
        "conversation_id": "telegram:user-1",
        "proposed_by": "nous_hermes_agent",
    }
    payload.update(overrides)
    return ToolRequest(**payload)


def test_tool_request_accepts_valid_payload() -> None:
    request = _tool_request()

    assert request.provider == "gmail"
    assert request.id
    assert request.created_at is not None


def test_tool_request_rejects_invalid_risk_level() -> None:
    with pytest.raises(ValidationError):
        _tool_request(risk_level=6)


def test_tool_decision_requires_exactly_one_outcome() -> None:
    with pytest.raises(ValidationError):
        ToolDecision(
            allow=True,
            deny=True,
            reason="Conflicting decision.",
            policy_rule="test.conflict",
        )

    with pytest.raises(ValidationError):
        ToolDecision(
            reason="Missing decision.",
            policy_rule="test.missing",
        )


def test_tool_decision_outcome_property() -> None:
    decision = ToolDecision(
        convert_to_draft=True,
        reason="Draft only.",
        policy_rule="gmail.draft_only",
    )

    assert decision.outcome == "convert_to_draft"
    assert decision.audit_id


def test_tool_execution_record_rejects_external_effect_without_execution() -> None:
    with pytest.raises(ValidationError):
        ToolExecutionRecord(
            tool_request_id="request-1",
            tool_decision_id="decision-1",
            trace_id="trace-1",
            conversation_id="telegram:user-1",
            tool_name="gmail.create_draft",
            provider="gmail",
            action="create_draft",
            risk_level=1,
            requires_approval=False,
            decision="convert_to_draft",
            execution_status="draft_proposed",
            executed=False,
            external_effect=True,
        )
