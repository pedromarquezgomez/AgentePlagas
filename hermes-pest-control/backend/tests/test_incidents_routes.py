from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

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
    **overrides: object,
) -> IncidentDraft:
    payload = {
        "conversation_id": f"telegram:{pest_type}",
        "channel": "telegram",
        "pest_type": pest_type,
        "location": location,
        "affected_area": "cocina",
        "priority": priority,
        "summary": f"Cliente informa de {pest_type}.",
    }
    payload.update(overrides)
    return IncidentDraft(**payload)


async def _seed_incidents(service: IncidentService) -> tuple[str, str]:
    high = await service.create_incident(_draft("cucarachas", "high"))
    medium = await service.create_incident(_draft("hormigas", "medium", "Málaga"))
    return high.id, medium.id


async def _seed_operational_incidents(service: IncidentService) -> tuple[str, str, str]:
    urgent = await service.create_incident(
        _draft(
            "COCKROACH",
            "high",
            severity="HIGH",
            operational_priority="URGENT",
            response_hours=24,
            assessment_reason="Posible riesgo alimentario.",
            visit_type="URGENT_TREATMENT",
            technician_level="STANDARD",
            dispatch_bucket="URGENT_24H",
            sla_hours=24,
            confidence="high",
        )
    )
    week = await service.create_incident(
        _draft(
            "ANT",
            "low",
            location="Málaga",
            severity="LOW",
            operational_priority="LOW",
            response_hours=72,
            assessment_reason="Presencia de hormigas.",
            visit_type="TREATMENT",
            technician_level="JUNIOR",
            dispatch_bucket="THIS_WEEK",
            sla_hours=72,
            confidence="high",
        )
    )
    legacy = await service.create_incident(
        _draft(
            "RODENT",
            "urgent",
            location="Fuengirola",
            metadata={
                "severity": "HIGH",
                "priority": "URGENT",
                "response_hours": 24,
                "assessment_reason": "Posible riesgo sanitario.",
                "visit_type": "URGENT_TREATMENT",
                "technician_level": "SENIOR",
                "dispatch_bucket": "URGENT_24H",
                "sla_hours": 24,
                "confidence": "high",
            },
        )
    )
    return urgent.id, week.id, legacy.id


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
        {"status": "closed"},
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


def test_get_incidents_exposes_operational_fields(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    anyio.run(_seed_operational_incidents, service)

    response = client.get("/incidents?pest_type=COCKROACH")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["pest_type"] == "COCKROACH"
    assert body[0]["severity"] == "HIGH"
    assert body[0]["operational_priority"] == "URGENT"
    assert body[0]["response_hours"] == 24
    assert body[0]["assessment_reason"] == "Posible riesgo alimentario."
    assert body[0]["visit_type"] == "URGENT_TREATMENT"
    assert body[0]["technician_level"] == "STANDARD"
    assert body[0]["dispatch_bucket"] == "URGENT_24H"
    assert body[0]["sla_hours"] == 24


def test_get_incident_flattens_operational_metadata(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    _, _, legacy_id = anyio.run(_seed_operational_incidents, service)

    response = client.get(f"/incidents/{legacy_id}")

    body = response.json()
    assert response.status_code == 200
    assert body["severity"] == "HIGH"
    assert body["operational_priority"] == "URGENT"
    assert body["dispatch_bucket"] == "URGENT_24H"


def test_get_incidents_filters_by_operational_priority_and_dispatch_bucket(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    urgent_id, _, legacy_id = anyio.run(_seed_operational_incidents, service)

    priority_response = client.get("/incidents?priority=URGENT")
    bucket_response = client.get("/incidents?dispatch_bucket=THIS_WEEK")

    assert priority_response.status_code == 200
    assert [item["id"] for item in priority_response.json()] == [urgent_id, legacy_id]
    assert bucket_response.status_code == 200
    assert [item["dispatch_bucket"] for item in bucket_response.json()] == ["THIS_WEEK"]


def test_get_incidents_sorts_by_sla_hours(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    anyio.run(_seed_operational_incidents, service)

    response = client.get("/incidents?sort_by=sla_hours&sort_dir=asc")

    assert response.status_code == 200
    assert [item["sla_hours"] for item in response.json()] == [24, 24, 72]


def test_get_incidents_exposes_and_filters_sla_status(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    urgent_id, week_id, _ = anyio.run(_seed_operational_incidents, service)
    anyio.run(
        firestore_service.update_document,
        "incidents",
        urgent_id,
        {"created_at": datetime.now(timezone.utc) - timedelta(hours=30)},
    )
    anyio.run(
        firestore_service.update_document,
        "incidents",
        week_id,
        {"created_at": datetime.now(timezone.utc) - timedelta(hours=70)},
    )

    breached_response = client.get("/incidents?sla_status=BREACHED")
    at_risk_response = client.get("/incidents?sla_status=AT_RISK")

    assert breached_response.status_code == 200
    assert [item["id"] for item in breached_response.json()] == [urgent_id]
    assert breached_response.json()[0]["sla_status"] == "BREACHED"
    assert breached_response.json()[0]["breach_hours"] > 0
    assert at_risk_response.status_code == 200
    assert [item["id"] for item in at_risk_response.json()] == [week_id]
    assert at_risk_response.json()[0]["remaining_hours"] <= 18


def test_get_incidents_sorts_by_remaining_hours(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    urgent_id, week_id, _ = anyio.run(_seed_operational_incidents, service)
    anyio.run(
        firestore_service.update_document,
        "incidents",
        urgent_id,
        {"created_at": datetime.now(timezone.utc) - timedelta(hours=10)},
    )
    anyio.run(
        firestore_service.update_document,
        "incidents",
        week_id,
        {"created_at": datetime.now(timezone.utc) - timedelta(hours=60)},
    )

    response = client.get("/incidents?sort_by=remaining_hours&sort_dir=asc")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids.index(week_id) < ids.index(urgent_id)


def test_get_incident_returns_404_for_missing_incident(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    response = client.get("/incidents/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found."


def test_patch_incident_updates_status(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    incident_id, _ = anyio.run(_seed_incidents, service)

    response = client.patch(
        f"/incidents/{incident_id}",
        json={"status": "ready_for_scheduling"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == incident_id
    assert body["status"] == "ready_for_scheduling"
    assert "updated_at" in body


def test_patch_incident_updates_priority(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    incident_id, _ = anyio.run(_seed_incidents, service)

    response = client.patch(
        f"/incidents/{incident_id}",
        json={"priority": "urgent"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["priority"] == "urgent"


def test_patch_incident_allows_internal_notes(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    incident_id, _ = anyio.run(_seed_incidents, service)

    response = client.patch(
        f"/incidents/{incident_id}",
        json={"internal_notes": "Llamar al cliente antes de planificar visita."},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["internal_notes"] == "Llamar al cliente antes de planificar visita."


def test_patch_incident_rejects_invalid_status(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    incident_id, _ = anyio.run(_seed_incidents, service)

    response = client.patch(
        f"/incidents/{incident_id}",
        json={"status": "resolved"},
    )

    assert response.status_code == 422


def test_patch_incident_returns_404_for_missing_incident(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    response = client.patch(
        "/incidents/missing",
        json={"status": "ready_for_scheduling"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found."


def test_patch_incident_rejects_arbitrary_fields(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    import anyio

    incident_id, _ = anyio.run(_seed_incidents, service)

    response = client.patch(
        f"/incidents/{incident_id}",
        json={"summary": "Intento de editar campo no permitido."},
    )

    assert response.status_code == 422
