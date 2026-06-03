import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.routes import incidents as incidents_route
from app.schemas.incident import IncidentDraft
from app.services.incident_service import IncidentService
from app.services.mock_firestore_service import MockFirestoreService
from app.incidents.work_queue.engine import WorkQueueEngine

client = TestClient(app)


def _draft(
    pest_type: str,
    priority: str,
    created_at: str | None = None,
    **overrides: object,
) -> IncidentDraft:
    payload = {
        "conversation_id": f"telegram:{pest_type.lower()}",
        "channel": "telegram",
        "pest_type": pest_type,
        "location": "Torremolinos",
        "affected_area": "cocina",
        "priority": priority,
        "summary": f"Cliente informa de {pest_type}.",
    }
    payload.update(overrides)
    draft_obj = IncidentDraft(**payload)
    return draft_obj


def test_work_queue_engine_rules() -> None:
    """Verifica individualmente las reglas de scoring del WorkQueueEngine."""
    # 1. Breached gana siempre
    score_breached = WorkQueueEngine.rank(
        prioridad="LOW",
        severidad="LOW",
        dispatch_bucket="MANUAL_REVIEW",
        sla_status="BREACHED",
        created_at=datetime.now(timezone.utc),
    )
    score_urgent = WorkQueueEngine.rank(
        prioridad="URGENT",
        severidad="CRITICAL",
        dispatch_bucket="URGENT_24H",
        sla_status="ON_TRACK",
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    assert score_breached.score > score_urgent.score

    # 2. At risk gana a on_track
    score_at_risk = WorkQueueEngine.rank(
        prioridad="LOW",
        severidad="LOW",
        dispatch_bucket="MANUAL_REVIEW",
        sla_status="AT_RISK",
        created_at=datetime.now(timezone.utc),
    )
    assert score_at_risk.score > score_urgent.score

    # 3. Urgent gana a normal/high en on_track
    score_on_track_urgent = WorkQueueEngine.rank(
        prioridad="URGENT",
        severidad="LOW",
        dispatch_bucket="MANUAL_REVIEW",
        sla_status="ON_TRACK",
        created_at=datetime.now(timezone.utc),
    )
    score_on_track_high = WorkQueueEngine.rank(
        prioridad="HIGH",
        severidad="CRITICAL",
        dispatch_bucket="URGENT_24H",
        sla_status="ON_TRACK",
        created_at=datetime.now(timezone.utc),
    )
    assert score_on_track_urgent.score > score_on_track_high.score

    # 4. Dispatch bucket URGENT_24H gana a NEXT_48H
    score_24h = WorkQueueEngine.rank(
        prioridad="LOW",
        severidad="LOW",
        dispatch_bucket="URGENT_24H",
        sla_status="ON_TRACK",
        created_at=datetime.now(timezone.utc),
    )
    score_48h = WorkQueueEngine.rank(
        prioridad="LOW",
        severidad="LOW",
        dispatch_bucket="NEXT_48H",
        sla_status="ON_TRACK",
        created_at=datetime.now(timezone.utc),
    )
    assert score_24h.score > score_48h.score

    # 5. Incidencia más antigua gana empate
    now = datetime.now(timezone.utc)
    score_antigua = WorkQueueEngine.rank(
        prioridad="HIGH",
        severidad="MEDIUM",
        dispatch_bucket="THIS_WEEK",
        sla_status="ON_TRACK",
        created_at=now - timedelta(hours=10),
    )
    score_reciente = WorkQueueEngine.rank(
        prioridad="HIGH",
        severidad="MEDIUM",
        dispatch_bucket="THIS_WEEK",
        sla_status="ON_TRACK",
        created_at=now - timedelta(hours=1),
    )
    assert score_antigua.score > score_reciente.score


@pytest.mark.asyncio
async def test_incident_service_work_queue_integration(monkeypatch) -> None:
    """Verifica que el IncidentService ordene y asigne posiciones correctamente."""
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)

    # Crear 3 incidencias con distintos niveles de prioridad
    # A: Breached (LOW) -> Debería quedar posición 1
    # B: At Risk (HIGH) -> Debería quedar posición 2
    # C: On Track (LOW, pero más antigua que D) -> Debería quedar posición 3
    # D: On Track (LOW, más nueva que C) -> Debería quedar posición 4
    # E: Closed (HIGH) -> Debería quedar posición None (inactiva)

    now = datetime.now(timezone.utc)
    
    # E
    inc_e = await service.create_incident(_draft("COCKROACH", "high"))
    await firestore_service.update_document("incidents", inc_e.id, {
        "status": "closed",
        "created_at": (now - timedelta(hours=20)).isoformat(),
    })
    
    # A
    inc_a = await service.create_incident(_draft("COCKROACH", "low", sla_hours=2))
    await firestore_service.update_document("incidents", inc_a.id, {"created_at": (now - timedelta(hours=5)).isoformat()})
    
    # B
    inc_b = await service.create_incident(_draft("RODENT", "high", sla_hours=10))
    await firestore_service.update_document("incidents", inc_b.id, {"created_at": (now - timedelta(hours=9)).isoformat()})
    
    # C
    inc_c = await service.create_incident(_draft("ANT", "low", sla_hours=72))
    await firestore_service.update_document("incidents", inc_c.id, {"created_at": (now - timedelta(hours=15)).isoformat()})
    
    # D
    inc_d = await service.create_incident(_draft("ANT", "low", sla_hours=72))
    await firestore_service.update_document("incidents", inc_d.id, {"created_at": (now - timedelta(hours=5)).isoformat()})

    # Realizar consulta
    response = client.get("/incidents")
    assert response.status_code == 200
    
    body = response.json()
    # Deben retornar todas
    assert len(body) == 5

    # Encontrar cada una en el resultado
    items = {item["id"]: item for item in body}

    # Validar posiciones en la cola
    assert items[inc_a.id]["queue_position"] == 1
    assert items[inc_b.id]["queue_position"] == 2
    assert items[inc_c.id]["queue_position"] == 3
    assert items[inc_d.id]["queue_position"] == 4
    assert items[inc_e.id]["queue_position"] is None

    # Validar que los scores van de mayor a menor para los activos
    assert items[inc_a.id]["queue_score"] > items[inc_b.id]["queue_score"]
    assert items[inc_b.id]["queue_score"] > items[inc_c.id]["queue_score"]
    assert items[inc_c.id]["queue_score"] > items[inc_d.id]["queue_score"]
    assert items[inc_e.id]["queue_score"] is None

    # Validar que las razones no estén vacías
    assert items[inc_a.id]["queue_reason"] == "SLA Incumplido (Breached)"
    assert items[inc_b.id]["queue_reason"] == "SLA en Riesgo (At Risk)"
    
    # Validar el orden por defecto devuelto por el API (debe coincidir con queue_position ascendente, None al final)
    returned_ids = [item["id"] for item in body]
    assert returned_ids[:4] == [inc_a.id, inc_b.id, inc_c.id, inc_d.id]
    assert returned_ids[4] == inc_e.id
