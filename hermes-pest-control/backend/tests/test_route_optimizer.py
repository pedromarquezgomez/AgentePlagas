import anyio
from fastapi.testclient import TestClient
from app.main import app
from app.services.mock_firestore_service import MockFirestoreService
from app.services.visit_service import VisitService
from app.schemas.visit import VisitCreate
from app.routes import calendar as calendar_route

client = TestClient(app)


async def _seed_test_visits(visit_service: VisitService) -> None:
    # Creamos tres visitas en orden subóptimo (primero Marbella, luego Torremolinos, luego Fuengirola)
    await visit_service.create_visit(
        VisitCreate(
            incident_id="inc-1",
            technician_id="tech-pedro",
            scheduled_start="2026-06-05T10:00:00Z",
            scheduled_end="2026-06-05T11:30:00Z",
            status="scheduled",
            address="Avenida Ricardo Soriano 24, Marbella",  # Lejos de Málaga (~50km)
            notes="Fumigación Marbella",
        )
    )
    await visit_service.create_visit(
        VisitCreate(
            incident_id="inc-2",
            technician_id="tech-pedro",
            scheduled_start="2026-06-05T12:00:00Z",
            scheduled_end="2026-06-05T13:30:00Z",
            status="scheduled",
            address="Calle San Miguel 14, Torremolinos",  # Cerca de Málaga (~15km)
            notes="Inspección Torremolinos",
        )
    )
    await visit_service.create_visit(
        VisitCreate(
            incident_id="inc-3",
            technician_id="tech-pedro",
            scheduled_start="2026-06-05T14:00:00Z",
            scheduled_end="2026-06-05T15:30:00Z",
            status="scheduled",
            address="Paseo Marítimo 52, Fuengirola",  # A mitad de camino (~30km)
            notes="Control Fuengirola",
        )
    )


def test_optimize_route_endpoint(monkeypatch) -> None:
    from app.services.firestore_factory import get_firestore_service
    mock_db = get_firestore_service()
    mock_db._collections.clear()  # Asegurar aislamiento del test

    visit_service = VisitService(mock_db)
    monkeypatch.setattr(calendar_route, "visit_service", visit_service)
    
    # Seedear las visitas
    anyio.run(_seed_test_visits, visit_service)

    # Llamar al endpoint de optimización
    response = client.post(
        "/calendar/optimize-route",
        json={
            "technician_id": "tech-pedro",
            "date": "2026-06-05",
            "apply": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["technician_id"] == "tech-pedro"
    assert body["original_distance_km"] > body["optimized_distance_km"]
    assert body["savings_percent"] > 0.0
    
    visits = body["visits"]
    assert len(visits) == 3
    assert "Torremolinos" in visits[0]["address"]
    assert "Fuengirola" in visits[1]["address"]
    assert "Marbella" in visits[2]["address"]
