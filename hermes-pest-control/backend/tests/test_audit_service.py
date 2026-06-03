from app.audit.contracts import AuditEvent, AuditEventType
from app.audit.in_memory_repository import InMemoryAuditRepository
from app.audit.service import AuditService


def test_record_audit_event() -> None:
    repository = InMemoryAuditRepository()
    service = AuditService(repository)

    event = AuditEvent(
        event_type=AuditEventType.TOOL_PROPOSED,
        execution_id="execution-1",
        tool_name="gmail.create_draft",
        provider="gmail",
        status="requested",
        message="Tool execution requested.",
    )

    service.record_event(event)

    assert repository.list_events() == [event]


def test_list_audit_events() -> None:
    repository = InMemoryAuditRepository()
    service = AuditService(repository)
    service.record_event(
        AuditEvent(
            event_type=AuditEventType.POLICY_EVALUATED,
            execution_id="execution-1",
            tool_name="gmail.create_draft",
            status="allow",
            message="Policy evaluated.",
        )
    )

    events = service.list_events()

    assert len(events) == 1
    assert events[0].event_type == AuditEventType.POLICY_EVALUATED


def test_list_audit_events_by_execution() -> None:
    repository = InMemoryAuditRepository()
    service = AuditService(repository)
    service.record_event(
        AuditEvent(
            event_type=AuditEventType.TOOL_PROPOSED,
            execution_id="execution-1",
            tool_name="gmail.create_draft",
        )
    )
    service.record_event(
        AuditEvent(
            event_type=AuditEventType.TOOL_PROPOSED,
            execution_id="execution-2",
            tool_name="calendar.propose_event",
        )
    )

    events = service.list_by_execution("execution-1")

    assert len(events) == 1
    assert events[0].execution_id == "execution-1"


def test_audit_service_failure_does_not_raise() -> None:
    class FailingRepository:
        def record_event(self, event: AuditEvent) -> None:
            raise RuntimeError("audit unavailable")

        def list_events(self) -> list[AuditEvent]:
            raise RuntimeError("audit unavailable")

        def list_by_execution(self, execution_id: str) -> list[AuditEvent]:
            raise RuntimeError("audit unavailable")

        def list_by_tool_name(self, tool_name: str) -> list[AuditEvent]:
            raise RuntimeError("audit unavailable")

    service = AuditService(FailingRepository())

    service.record_event(AuditEvent(event_type=AuditEventType.TOOL_PROPOSED))

    assert service.list_events() == []
    assert service.list_by_execution("execution-1") == []
    assert service.list_by_tool_name("gmail.create_draft") == []
