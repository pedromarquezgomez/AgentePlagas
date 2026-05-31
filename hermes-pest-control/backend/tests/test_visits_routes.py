from fastapi.testclient import TestClient

from app.dependencies import admin_auth
from app.main import app
from app.routes import visits as visits_route
from app.schemas.visit import VisitCreate
from app.services.mock_firestore_service import MockFirestoreService
from app.services.visit_service import VisitService


client = TestClient(app)


async def _seed_visits(service: VisitService) -> tuple[str, str]:
    first = await service.create_visit(
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
    second = await service.create_visit(
        VisitCreate(
            incident_id="incident-2",
            technician_id="technician-2",
            scheduled_start="2026-06-02T11:00:00+02:00",
            scheduled_end="2026-06-02T12:00:00+02:00",
            status="draft",
            address="Calle Ejemplo 2, Málaga",
        )
    )
    return first.id, second.id


def test_create_visit(monkeypatch) -> None:
    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)

    response = client.post(
        "/visits",
        json={
            "incident_id": "incident-1",
            "technician_id": "technician-1",
            "scheduled_start": "2026-06-01T09:00:00+02:00",
            "scheduled_end": "2026-06-01T10:00:00+02:00",
            "status": "scheduled",
            "address": "Calle Ejemplo 1, Torremolinos",
            "notes": "Primera visita.",
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["id"] is not None
    assert body["incident_id"] == "incident-1"
    assert body["status"] == "scheduled"


def test_list_visits(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    anyio.run(_seed_visits, service)

    response = client.get("/visits")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 2


def test_list_visits_filters_by_incident_id(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    first_id, _ = anyio.run(_seed_visits, service)

    response = client.get("/visits?incident_id=incident-1")

    body = response.json()
    assert response.status_code == 200
    assert [visit["id"] for visit in body] == [first_id]


def test_list_visits_filters_by_technician_and_status(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    first_id, _ = anyio.run(_seed_visits, service)

    response = client.get("/visits?technician_id=technician-1&status=scheduled")

    body = response.json()
    assert response.status_code == 200
    assert [visit["id"] for visit in body] == [first_id]


def test_get_visit(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    visit_id, _ = anyio.run(_seed_visits, service)

    response = client.get(f"/visits/{visit_id}")

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == visit_id
    assert body["incident_id"] == "incident-1"


def test_update_visit(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    visit_id, _ = anyio.run(_seed_visits, service)

    response = client.patch(
        f"/visits/{visit_id}",
        json={
            "status": "in_progress",
            "technician_id": "technician-3",
            "notes": "Técnico reasignado manualmente.",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "in_progress"
    assert body["technician_id"] == "technician-3"
    assert body["notes"] == "Técnico reasignado manualmente."


def test_patch_visit_rejects_arbitrary_fields(monkeypatch) -> None:
    import anyio

    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    visit_id, _ = anyio.run(_seed_visits, service)

    response = client.patch(
        f"/visits/{visit_id}",
        json={"metadata": {"route_optimization": True}},
    )

    assert response.status_code == 422


def test_visits_endpoint_requires_admin_auth(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/visits")

    assert response.status_code == 401
    assert "test-admin-key" not in response.text


def test_visits_endpoint_accepts_admin_auth(monkeypatch) -> None:
    service = VisitService(MockFirestoreService())
    monkeypatch.setattr(visits_route, "visit_service", service)
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/visits",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200
