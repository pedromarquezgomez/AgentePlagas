from app.audit.contracts import AuditEvent
from app.audit.in_memory_repository import InMemoryAuditRepository


_default_repository = InMemoryAuditRepository()


class AuditService:
    def __init__(self, repository: InMemoryAuditRepository | None = None) -> None:
        self.repository = repository or _default_repository

    def record_event(self, event: AuditEvent) -> None:
        try:
            self.repository.record_event(event)
        except Exception:
            # Audit is best-effort and must never break the operational flow.
            return

    def list_events(self) -> list[AuditEvent]:
        try:
            return self.repository.list_events()
        except Exception:
            return []

    def list_by_execution(self, execution_id: str) -> list[AuditEvent]:
        try:
            return self.repository.list_by_execution(execution_id)
        except Exception:
            return []

    def list_by_tool_name(self, tool_name: str) -> list[AuditEvent]:
        try:
            return self.repository.list_by_tool_name(tool_name)
        except Exception:
            return []


def default_audit_service() -> AuditService:
    return AuditService(_default_repository)
