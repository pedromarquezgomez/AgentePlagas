import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta

from app.main import app
from app.config.settings import settings
from app.services.google_calendar_service import GoogleCalendarService

client = TestClient(app)


def test_calendar_status_endpoint() -> None:
    """Verifica que el endpoint temporal GET /calendar/status responda con la estructura correcta."""
    headers = {}
    if settings.admin_api_key:
        headers["X-Admin-API-Key"] = settings.admin_api_key

    response = client.get("/calendar/status", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "calendar_enabled" in body
    assert body["provider"] == "google_calendar"
    assert "authentication" in body
    assert "calendar_id" in body
    assert "can_read" in body
    assert "can_write" in body


@pytest.mark.skipif(
    not settings.google_calendar_enabled,
    reason="Google Calendar is disabled. Skip real verification.",
)
@pytest.mark.asyncio
async def test_real_google_calendar_lifecycle() -> None:
    """Crea, lee y elimina un evento real en Google Calendar si la integración está activa."""
    gcal = GoogleCalendarService()
    
    # 1. Crear evento
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    
    visit_data = {
        "incident_id": "real-test-incident-999",
        "notes": "Prueba de integración real Google Calendar",
        "address": "Calle de Prueba 123, Málaga",
        "scheduled_start": start_time.isoformat(),
        "scheduled_end": end_time.isoformat(),
    }
    
    # Crear
    created_event = await gcal.create_event_for_visit(visit_data)
    assert created_event is not None
    event_id = created_event.get("id")
    assert event_id is not None
    
    try:
        # 2. Leer
        fetched_event = await gcal.get_event(event_id)
        assert fetched_event is not None
        assert fetched_event.get("id") == event_id
        assert "real-test-incident-999" in fetched_event.get("summary", "")
    finally:
        # 3. Eliminar
        deleted = await gcal.delete_event(event_id)
        assert deleted.get("status") == "deleted"
        assert deleted.get("event_id") == event_id
