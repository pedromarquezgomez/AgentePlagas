from fastapi.testclient import TestClient

from app.main import app
from app.routes import incidents as incidents_route
from app.schemas.incident import IncidentDraft
from app.services.incident_service import IncidentService
from app.services.mock_firestore_service import MockFirestoreService


client = TestClient(app)


def _draft(
    pest_type: str,
    priority: str,
    location: str = "Torremolinos",
) -> IncidentDraft:
    return IncidentDraft(
        conversation_id=f"telegram:{pest_type}",
        channel="telegram",
        pest_type=pest_type,
        location=location,
        affected_area="cocina",
        priority=priority,
        summary=f"Cliente informa de {pest_type}.",
    )


async def _seed_incidents(service: IncidentService) -> tuple[str, str]:
    high = await service.create_incident(_draft("cucarachas", "high"))
    medium = await service.create_incident(_draft("hormigas", "medium", "Málaga"))
    return high.id, medium.id


def test_get_incidents_returns_list(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    anyio.run(_seed_incidents, service)

    response = client.get("/incidents")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 2
    assert body[0]["id"] is not None


def test_get_incidents_filters_by_status(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    first_id, second_id = anyio.run(_seed_incidents, service)
    anyio.run(
        firestore_service.update_document,
        "incidents",
        second_id,
        {"status": "resolved"},
    )

    response = client.get("/incidents?status=pending_review")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["id"] == first_id
    assert body[0]["status"] == "pending_review"


def test_get_incident_returns_detail(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    incident_id, _ = anyio.run(_seed_incidents, service)

    response = client.get(f"/incidents/{incident_id}")

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == incident_id
    assert body["pest_type"] == "cucarachas"


def test_get_incident_returns_404_for_missing_incident(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    response = client.get("/incidents/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found."
