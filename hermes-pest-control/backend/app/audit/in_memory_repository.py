from app.audit.contracts import AuditEvent


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record_event(self, event: AuditEvent) -> None:
        self._events.append(event)

    def list_events(self) -> list[AuditEvent]:
        return list(self._events)

    def list_by_execution(self, execution_id: str) -> list[AuditEvent]:
        return [
            event
            for event in self._events
            if event.execution_id == execution_id
        ]

    def list_by_tool_name(self, tool_name: str) -> list[AuditEvent]:
        return [
            event
            for event in self._events
            if event.tool_name == tool_name
        ]

    def clear(self) -> None:
        self._events.clear()
