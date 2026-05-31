from fastapi.testclient import TestClient

from app.dependencies import admin_auth
from app.main import app
from app.routes import calendar as calendar_route
from app.schemas.visit import VisitCreate
from app.services.mock_firestore_service import MockFirestoreService
from app.services.visit_service import VisitService

client = TestClient(app)


async def _seed_calendar_visits(service: VisitService) -> tuple[str, str, str]:
    first = await service.create_visit(
        VisitCreate(
            incident_id="incident-1",
            technician_id="technician-1",
            scheduled_start="2026-06-01T09:00:00+02:00",
            scheduled_end="2026-06-01T10:00:00+02:00",
            status="scheduled",
        )
    )
    second = await service.create_visit(
        VisitCreate(
            incident_id="incident-2",
            technician_id="technician-2",
            scheduled_start="2026-06-03T11:00:00+02:00",
            scheduled_end="2026-06-03T12:00:00+02:00",
            status="in_progress",
        )
    )
    outside_range = await service.create_visit(
        VisitCreate(
            incident_id="incident-3",
            technician_id="technician-1",
            scheduled_start="2026-06-10T09:00:00+02:00",
            status="scheduled",
        )
    )
    return first.id or "", second.id or "", outside_range.id or ""


def test_calendar_visits_returns_valid_range(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(calendar_route, "visit_service", service)
    first_id, second_id, _ = anyio.run(_seed_calendar_visits, service)

    response = client.get("/calendar/visits?start_date=2026-06-01&end_date=2026-06-07")

    body = response.json()
    assert response.status_code == 200
    assert [visit["id"] for visit in body] == [first_id, second_id]


def test_calendar_visits_filters_by_technician(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(calendar_route, "visit_service", service)
    first_id, _, _ = anyio.run(_seed_calendar_visits, service)

    response = client.get(
        "/calendar/visits?start_date=2026-06-01&end_date=2026-06-07"
        "&technician_id=technician-1"
    )

    body = response.json()
    assert response.status_code == 200
    assert [visit["id"] for visit in body] == [first_id]


def test_calendar_visits_filters_by_status(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(calendar_route, "visit_service", service)
    _, second_id, _ = anyio.run(_seed_calendar_visits, service)

    response = client.get(
        "/calendar/visits?start_date=2026-06-01&end_date=2026-06-07"
        "&status=in_progress"
    )

    body = response.json()
    assert response.status_code == 200
    assert [visit["id"] for visit in body] == [second_id]


def test_calendar_visits_requires_dates() -> None:
    response = client.get("/calendar/visits")

    assert response.status_code == 422


def test_calendar_visits_rejects_invalid_range() -> None:
    response = client.get("/calendar/visits?start_date=2026-06-07&end_date=2026-06-01")

    assert response.status_code == 422


def test_calendar_visits_requires_admin_auth(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/calendar/visits?start_date=2026-06-01&end_date=2026-06-07")

    assert response.status_code == 401
    assert "test-admin-key" not in response.text


def test_calendar_visits_accepts_admin_auth(monkeypatch) -> None:
    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(calendar_route, "visit_service", service)
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/calendar/visits?start_date=2026-06-01&end_date=2026-06-07",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200
