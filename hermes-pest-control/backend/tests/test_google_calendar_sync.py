from fastapi.testclient import TestClient

from app.dependencies import admin_auth
from app.main import app
from app.routes import visits as visits_route
from app.schemas.visit import VisitCreate
from app.services.mock_firestore_service import MockFirestoreService
from app.services.visit_service import VisitService

client = TestClient(app)


class DisabledCalendarService:
    provider = "google"
    enabled = False


class MockGoogleCalendarService:
    provider = "google"
    enabled = True

    def __init__(self) -> None:
        self.created_visits: list[dict] = []
        self.updated_visits: list[tuple[dict, str]] = []

    async def create_event_for_visit(self, visit: dict) -> dict:
        self.created_visits.append(visit)
        return {"id": "google-event-1"}

    async def update_event_for_visit(self, visit: dict, event_id: str) -> dict:
        self.updated_visits.append((visit, event_id))
        return {"id": event_id}


async def _seed_visit(service: VisitService) -> str:
    visit = await service.create_visit(
        VisitCreate(
            incident_id="incident-1",
            technician_id="technician-1",
            scheduled_start="2026-06-01T09:00:00+02:00",
            scheduled_end="2026-06-01T10:00:00+02:00",
            status="scheduled",
            address="Calle Ejemplo 1, Torremolinos",
            notes="Primera visita.",
        )
    )
    return visit.id or ""


def test_sync_calendar_disabled_returns_skipped(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    monkeypatch.setattr(visits_route, "google_calendar_service", DisabledCalendarService())
    visit_id = anyio.run(_seed_visit, service)

    response = client.post(f"/visits/{visit_id}/sync-calendar")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "skipped"
    assert body["reason"] == "google_calendar_disabled"
    assert body["visit"]["external_calendar_event_id"] is None


def test_sync_calendar_with_mock_creates_event_id(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    google_calendar_service = MockGoogleCalendarService()
    monkeypatch.setattr(visits_route, "visit_service", service)
    monkeypatch.setattr(visits_route, "google_calendar_service", google_calendar_service)
    visit_id = anyio.run(_seed_visit, service)

    response = client.post(f"/visits/{visit_id}/sync-calendar")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "synced"
    assert body["visit"]["external_calendar_provider"] == "google"
    assert body["visit"]["external_calendar_event_id"] == "google-event-1"
    assert google_calendar_service.created_visits[0]["id"] == visit_id


def test_sync_calendar_updates_visit_sync_status(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    monkeypatch.setattr(visits_route, "google_calendar_service", MockGoogleCalendarService())
    visit_id = anyio.run(_seed_visit, service)

    response = client.post(f"/visits/{visit_id}/sync-calendar")
    refreshed = client.get(f"/visits/{visit_id}").json()

    assert response.status_code == 200
    assert refreshed["external_calendar_sync_status"] == "synced"
    assert refreshed["external_calendar_last_synced_at"] is not None
    assert refreshed["external_calendar_error"] is None


def test_sync_calendar_missing_visit_returns_404(monkeypatch) -> None:
    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    monkeypatch.setattr(visits_route, "google_calendar_service", MockGoogleCalendarService())

    response = client.post("/visits/missing/sync-calendar")

    assert response.status_code == 404


def test_sync_calendar_requires_admin_auth(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.post("/visits/visit-1/sync-calendar")

    assert response.status_code == 401
    assert "test-admin-key" not in response.text


def test_sync_calendar_accepts_admin_auth(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    monkeypatch.setattr(visits_route, "google_calendar_service", DisabledCalendarService())
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")
    visit_id = anyio.run(_seed_visit, service)

    response = client.post(
        f"/visits/{visit_id}/sync-calendar",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200
