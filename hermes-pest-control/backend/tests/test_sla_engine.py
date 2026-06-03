from datetime import datetime, timedelta, timezone

import anyio

from app.audit.contracts import AuditEventType
from app.audit.in_memory_repository import InMemoryAuditRepository
from app.audit.service import AuditService
from app.incidents.sla.contracts import SLAStatus
from app.incidents.sla.engine import SLAEngine
from app.schemas.incident import IncidentDraft
from app.services.incident_service import IncidentService
from app.services.mock_firestore_service import MockFirestoreService


CURRENT_TIME = datetime(2030, 1, 2, 12, 0, tzinfo=timezone.utc)


class FixedTimeSLAEngine(SLAEngine):
    def assess(self, **kwargs):
        kwargs["current_time"] = CURRENT_TIME
        return super().assess(**kwargs)


def test_sla_on_track_with_remaining_hours() -> None:
    assessment = SLAEngine().assess(
        incident_created_at=CURRENT_TIME - timedelta(hours=10),
        incident_status="pending_review",
        sla_hours=24,
        current_time=CURRENT_TIME,
        incident_id="incident-1",
    )

    assert assessment.sla_status == SLAStatus.ON_TRACK
    assert assessment.elapsed_hours == 10
    assert assessment.remaining_hours == 14
    assert assessment.breach_hours is None
    assert assessment.is_overdue is False


def test_sla_at_risk_within_last_25_percent() -> None:
    assessment = SLAEngine().assess(
        incident_created_at=CURRENT_TIME - timedelta(hours=20),
        incident_status="pending_review",
        sla_hours=24,
        current_time=CURRENT_TIME,
    )

    assert assessment.sla_status == SLAStatus.AT_RISK
    assert assessment.remaining_hours == 4
    assert assessment.breach_hours is None


def test_sla_breached_with_breach_hours() -> None:
    assessment = SLAEngine().assess(
        incident_created_at=CURRENT_TIME - timedelta(hours=30),
        incident_status="pending_review",
        sla_hours=24,
        current_time=CURRENT_TIME,
    )

    assert assessment.sla_status == SLAStatus.BREACHED
    assert assessment.remaining_hours == 0
    assert assessment.breach_hours == 6
    assert assessment.is_overdue is True


def test_sla_completed_when_incident_is_closed() -> None:
    assessment = SLAEngine().assess(
        incident_created_at=CURRENT_TIME - timedelta(hours=30),
        incident_status="closed",
        sla_hours=24,
        current_time=CURRENT_TIME,
    )

    assert assessment.sla_status == SLAStatus.COMPLETED
    assert assessment.remaining_hours == 0
    assert assessment.breach_hours is None
    assert assessment.is_overdue is False


def test_sla_breach_audit_is_recorded_once() -> None:
    firestore_service = MockFirestoreService()
    audit_repository = InMemoryAuditRepository()
    service = IncidentService(
        firestore_service,
        audit_service=AuditService(audit_repository),
        sla_engine=FixedTimeSLAEngine(),
    )

    async def scenario() -> None:
        incident = await service.create_incident(
            IncidentDraft(
                conversation_id="telegram:user-1",
                channel="telegram",
                pest_type="COCKROACH",
                location="Torremolinos",
                affected_area="cocina",
                priority="high",
                summary="Aviso con SLA vencido.",
                sla_hours=24,
            )
        )
        await firestore_service.update_document(
            "incidents",
            incident.id or "",
            {"created_at": CURRENT_TIME - timedelta(hours=30)},
        )
        await service.get_incident(incident.id or "")
        await service.get_incident(incident.id or "")

    anyio.run(scenario)

    events = [
        event
        for event in audit_repository.list_events()
        if event.event_type == AuditEventType.INCIDENT_SLA_BREACHED
    ]
    assert len(events) == 1
    assert events[0].metadata["breach_hours"] == 6
