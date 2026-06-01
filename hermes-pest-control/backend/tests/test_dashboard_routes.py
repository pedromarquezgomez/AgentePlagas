from fastapi.testclient import TestClient

from app.dependencies import admin_auth
from app.main import app
from app.routes import dashboard as dashboard_route
from app.schemas.human_review import HumanReviewItemCreate
from app.schemas.incident import IncidentDraft
from app.schemas.technician import TechnicianCreate
from app.schemas.visit import VisitCreate
from app.services.human_review_service import HumanReviewService
from app.services.incident_service import IncidentService
from app.services.mock_firestore_service import MockFirestoreService
from app.services.technician_service import TechnicianService
from app.services.visit_service import VisitService

client = TestClient(app)


def _install_dashboard_services(monkeypatch) -> tuple[
    IncidentService,
    HumanReviewService,
    VisitService,
    TechnicianService,
]:
    firestore_service = MockFirestoreService()
    incident_service = IncidentService(firestore_service)
    human_review_service = HumanReviewService(firestore_service)
    visit_service = VisitService(firestore_service)
    technician_service = TechnicianService(firestore_service)

    monkeypatch.setattr(dashboard_route, "incident_service", incident_service)
    monkeypatch.setattr(dashboard_route, "human_review_service", human_review_service)
    monkeypatch.setattr(dashboard_route, "visit_service", visit_service)
    monkeypatch.setattr(dashboard_route, "technician_service", technician_service)

    return incident_service, human_review_service, visit_service, technician_service


async def _seed_dashboard_data(
    incident_service: IncidentService,
    human_review_service: HumanReviewService,
    visit_service: VisitService,
    technician_service: TechnicianService,
) -> None:
    pending = await incident_service.create_incident(
        IncidentDraft(
            conversation_id="telegram:1",
            channel="telegram",
            pest_type="cucarachas",
            location="Torremolinos",
            affected_area="cocina",
            priority="urgent",
            summary="Aviso urgente pendiente de revisión.",
        )
    )
    ready = await incident_service.create_incident(
        IncidentDraft(
            conversation_id="telegram:2",
            channel="telegram",
            pest_type="roedores",
            location="Málaga",
            affected_area="garaje",
            priority="medium",
            summary="Aviso listo para agendar.",
        )
    )
    await incident_service.update_incident(
        ready.id or "",
        {"status": "ready_for_scheduling"},
    )

    await human_review_service.create_review_item(
        HumanReviewItemCreate(
            trace_id="trace-1",
            conversation_id="telegram:1",
            incident_id=pending.id,
            channel="telegram",
            reason="urgent_priority",
            priority="urgent",
            summary="Revisión por urgencia.",
        )
    )
    await human_review_service.create_review_item(
        HumanReviewItemCreate(
            trace_id="trace-2",
            conversation_id="telegram:2",
            channel="telegram",
            reason="agent_escalation",
            priority="medium",
            summary="Revisión resuelta.",
        )
    )

    await visit_service.create_visit(
        VisitCreate(
            incident_id=pending.id or "incident-1",
            status="scheduled",
            scheduled_start="2030-01-01T09:00:00+02:00",
        )
    )
    await visit_service.create_visit(
        VisitCreate(
            incident_id=ready.id or "incident-2",
            status="in_progress",
            scheduled_start="2030-01-02T09:00:00+02:00",
        )
    )
    await visit_service.create_visit(
        VisitCreate(
            incident_id=ready.id or "incident-2",
            status="completed",
            scheduled_start="2030-01-03T09:00:00+02:00",
        )
    )

    await technician_service.create_technician(
        TechnicianCreate(name="Ana Técnica", active=True)
    )
    await technician_service.create_technician(
        TechnicianCreate(name="Luis Técnico", active=False)
    )


def test_dashboard_summary_requires_admin_auth(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/dashboard/summary")

    assert response.status_code == 401
    assert "test-admin-key" not in response.text


def test_dashboard_summary_accepts_admin_auth(monkeypatch) -> None:
    _install_dashboard_services(monkeypatch)
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/dashboard/summary",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200


def test_dashboard_summary_returns_expected_structure(monkeypatch) -> None:
    _install_dashboard_services(monkeypatch)

    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    assert response.json() == {
        "incidents": {
            "total": 0,
            "pending_review": 0,
            "urgent": 0,
            "ready_for_scheduling": 0,
        },
        "human_review": {
            "open": 0,
            "urgent": 0,
        },
        "visits": {
            "total": 0,
            "scheduled": 0,
            "in_progress": 0,
            "completed": 0,
            "today": 0,
            "scheduled_this_week": 0,
        },
        "technicians": {
            "total": 0,
            "active": 0,
        },
    }


def test_dashboard_summary_counts_operational_data(monkeypatch) -> None:
    import anyio

    services = _install_dashboard_services(monkeypatch)
    anyio.run(_seed_dashboard_data, *services)

    response = client.get("/dashboard/summary")

    body = response.json()
    assert response.status_code == 200
    assert body["incidents"] == {
        "total": 2,
        "pending_review": 1,
        "urgent": 1,
        "ready_for_scheduling": 1,
    }
    assert body["human_review"] == {
        "open": 2,
        "urgent": 1,
    }
    assert body["visits"] == {
        "total": 3,
        "scheduled": 1,
        "in_progress": 1,
        "completed": 1,
        "today": 0,
        "scheduled_this_week": 0,
    }
    assert body["technicians"] == {
        "total": 2,
        "active": 1,
    }
