from app.tools.execution_contracts import (
    ToolExecutionError,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
)


def test_request_contract() -> None:
    request = ToolExecutionRequest(
        execution_id="execution-1",
        tool_name="gmail.create_draft",
        requested_by="operator@example.test",
        provider="gmail",
        payload={
            "recipient": "cliente@example.test",
            "subject": "Resumen",
            "body": "Borrador de prueba.",
        },
        trace_id="trace-1",
        conversation_id="telegram:user-1",
    )

    assert request.execution_id == "execution-1"
    assert request.tool_name == "gmail.create_draft"
    assert request.requested_by == "operator@example.test"
    assert request.provider == "gmail"
    assert request.payload["subject"] == "Resumen"
    assert request.created_at is not None


def test_result_contract() -> None:
    result = ToolExecutionResult(
        execution_id="execution-1",
        tool_name="gmail.create_draft",
        status=ToolExecutionStatus.EXECUTED,
        message="Tool execution completed.",
        result={"draft_id": "draft-1", "message_id": "message-1"},
    )

    assert result.status == ToolExecutionStatus.EXECUTED
    assert result.result["draft_id"] == "draft-1"
    assert result.executed_at is not None


def test_error_contract() -> None:
    error = ToolExecutionError(
        execution_id="execution-1",
        tool_name="gmail.send_email",
        error_code="policy_denied",
        error_message="Tool execution blocked by policy.",
    )

    assert error.error_code == "policy_denied"
    assert error.error_message == "Tool execution blocked by policy."


def test_status_lifecycle() -> None:
    approved_path = [
        ToolExecutionStatus.PENDING,
        ToolExecutionStatus.APPROVED,
        ToolExecutionStatus.EXECUTED,
    ]
    denied_path = [
        ToolExecutionStatus.PENDING,
        ToolExecutionStatus.DENIED,
    ]
    human_review_path = [
        ToolExecutionStatus.PENDING,
        ToolExecutionStatus.REQUIRES_HUMAN_REVIEW,
    ]

    assert approved_path == [
        ToolExecutionStatus.PENDING,
        ToolExecutionStatus.APPROVED,
        ToolExecutionStatus.EXECUTED,
    ]
    assert denied_path[-1] == ToolExecutionStatus.DENIED
    assert human_review_path[-1] == ToolExecutionStatus.REQUIRES_HUMAN_REVIEW
