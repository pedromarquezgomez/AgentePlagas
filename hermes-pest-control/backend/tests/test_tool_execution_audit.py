import anyio
from fastapi.testclient import TestClient

from app.audit.contracts import AuditEvent, AuditEventType
from app.audit.in_memory_repository import InMemoryAuditRepository
from app.audit.service import AuditService
from app.main import app
from app.routes import tools as tools_route
from app.schemas.tool_harness import ToolExecutionRecord
from app.services.gmail_tool_executor import GmailToolExecutionError
from app.services.mock_firestore_service import MockFirestoreService
from app.services.tool_execution_service import ToolExecutionService


client = TestClient(app)


def _record(**overrides: object) -> ToolExecutionRecord:
    payload = {
        "tool_request_id": "request-1",
        "tool_decision_id": "decision-1",
        "trace_id": "trace-1",
        "conversation_id": "telegram:user-1",
        "tool_name": "gmail.create_draft",
        "provider": "gmail",
        "action": "create_draft",
        "risk_level": 1,
        "requires_approval": False,
        "decision": "convert_to_draft",
        "execution_status": "draft_proposed",
        "review_status": "approved",
        "executed": False,
        "external_effect": False,
        "metadata": {
            "external_tools_executed": False,
            "payload": {
                "recipient": "cliente@example.test",
                "subject": "Resumen",
                "body": "Borrador de prueba.",
            },
        },
    }
    payload.update(overrides)
    return ToolExecutionRecord(**payload)


def _configure_route(monkeypatch, audit_service: AuditService) -> ToolExecutionService:
    service = ToolExecutionService(MockFirestoreService(), audit_service=audit_service)
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    monkeypatch.setattr(tools_route, "audit_service", audit_service)
    return service


def _event_types(audit_service: AuditService) -> list[AuditEventType]:
    return [event.event_type for event in audit_service.list_events()]


def test_policy_allow_is_audited(monkeypatch) -> None:
    class MockGmailExecutor:
        async def create_draft(self, payload: dict) -> dict:
            return {"provider": "gmail", "draft_id": "draft-1"}

    audit_service = AuditService(InMemoryAuditRepository())
    service = _configure_route(monkeypatch, audit_service)
    monkeypatch.setattr(tools_route, "gmail_tool_executor", MockGmailExecutor())
    record = anyio.run(service.create_execution_record, _record())

    response = client.post(f"/tools/executions/{record.id}/execute")

    assert response.status_code == 200
    policy_events = [
        event
        for event in audit_service.list_events()
        if event.event_type == AuditEventType.POLICY_EVALUATED
    ]
    assert policy_events
    assert policy_events[0].policy_decision == "ALLOW"


def test_policy_deny_is_audited(monkeypatch) -> None:
    audit_service = AuditService(InMemoryAuditRepository())
    service = _configure_route(monkeypatch, audit_service)
    record = anyio.run(
        service.create_execution_record,
        _record(
            tool_name="gmail.send_email",
            action="send_email",
            decision="deny",
            execution_status="blocked",
        ),
    )

    response = client.post(f"/tools/executions/{record.id}/execute")

    assert response.status_code == 403
    policy_events = [
        event
        for event in audit_service.list_events()
        if event.event_type == AuditEventType.POLICY_EVALUATED
    ]
    assert policy_events
    assert policy_events[0].policy_decision == "DENY"
    assert AuditEventType.TOOL_EXECUTION_STARTED not in _event_types(audit_service)


def test_human_review_required_is_audited(monkeypatch) -> None:
    audit_service = AuditService(InMemoryAuditRepository())
    service = _configure_route(monkeypatch, audit_service)
    record = anyio.run(
        service.create_execution_record,
        _record(
            tool_name="suggest_visit_tool",
            provider="llm",
            action="suggest_visit",
            risk_level=3,
            requires_approval=True,
            decision="require_human_approval",
            execution_status="pending_human_approval",
        ),
    )

    response = client.post(f"/tools/executions/{record.id}/execute")

    assert response.status_code == 409
    assert AuditEventType.HUMAN_REVIEW_REQUIRED in _event_types(audit_service)
    assert AuditEventType.TOOL_EXECUTION_STARTED not in _event_types(audit_service)


def test_tool_execution_success_is_audited(monkeypatch) -> None:
    class MockGmailExecutor:
        async def create_draft(self, payload: dict) -> dict:
            return {"provider": "gmail", "draft_id": "draft-1"}

    audit_service = AuditService(InMemoryAuditRepository())
    service = _configure_route(monkeypatch, audit_service)
    monkeypatch.setattr(tools_route, "gmail_tool_executor", MockGmailExecutor())
    record = anyio.run(service.create_execution_record, _record())

    response = client.post(f"/tools/executions/{record.id}/execute")

    assert response.status_code == 200
    event_types = _event_types(audit_service)
    assert AuditEventType.TOOL_EXECUTION_STARTED in event_types
    assert AuditEventType.TOOL_EXECUTION_COMPLETED in event_types


def test_tool_execution_failure_is_audited(monkeypatch) -> None:
    class MockGmailExecutor:
        async def create_draft(self, payload: dict) -> dict:
            raise GmailToolExecutionError("Could not create Gmail draft.")

    audit_service = AuditService(InMemoryAuditRepository())
    service = _configure_route(monkeypatch, audit_service)
    monkeypatch.setattr(tools_route, "gmail_tool_executor", MockGmailExecutor())
    record = anyio.run(service.create_execution_record, _record())

    response = client.post(f"/tools/executions/{record.id}/execute")

    assert response.status_code == 502
    failed_events = [
        event
        for event in audit_service.list_events()
        if event.event_type == AuditEventType.TOOL_EXECUTION_FAILED
    ]
    assert failed_events
    assert failed_events[0].metadata["error_code"] == "gmail_execution_failed"


def test_audit_failure_does_not_break_execution(monkeypatch) -> None:
    class FailingRepository:
        def record_event(self, event: AuditEvent) -> None:
            raise RuntimeError("audit unavailable")

        def list_events(self) -> list[AuditEvent]:
            raise RuntimeError("audit unavailable")

        def list_by_execution(self, execution_id: str) -> list[AuditEvent]:
            raise RuntimeError("audit unavailable")

        def list_by_tool_name(self, tool_name: str) -> list[AuditEvent]:
            raise RuntimeError("audit unavailable")

    class MockGmailExecutor:
        async def create_draft(self, payload: dict) -> dict:
            return {"provider": "gmail", "draft_id": "draft-1"}

    audit_service = AuditService(FailingRepository())
    service = _configure_route(monkeypatch, audit_service)
    monkeypatch.setattr(tools_route, "gmail_tool_executor", MockGmailExecutor())
    record = anyio.run(service.create_execution_record, _record())

    response = client.post(f"/tools/executions/{record.id}/execute")

    assert response.status_code == 200
    assert response.json()["executed"] is True
