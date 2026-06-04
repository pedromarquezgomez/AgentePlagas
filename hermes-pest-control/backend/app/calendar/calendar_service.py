from datetime import datetime, timezone
import logging
import asyncio
from typing import Any

from app.calendar.contracts import CalendarEventDraft
from app.services.google_calendar_service import GoogleCalendarService, GoogleCalendarServiceError

logger = logging.getLogger(__name__)

class HermesCalendarService:
    def __init__(self, google_cal_service: GoogleCalendarService | None = None) -> None:
        self.google_cal = google_cal_service or GoogleCalendarService()

    async def get_busy_slots(self, start_iso: str, end_iso: str) -> list[tuple[datetime, datetime]]:
        """
        Consulta los slots ocupados (busy) entre dos fechas ISO 8601.
        Si la integración está inactiva o falla, devuelve una lista vacía de forma segura.
        """
        if not self.google_cal.enabled:
            logger.info("Google Calendar integration is disabled. Returning empty busy slots.")
            return []

        try:
            service = self.google_cal._build_service()
            calendar_id = self.google_cal.settings.google_calendar_id
            
            body = {
                "timeMin": start_iso,
                "timeMax": end_iso,
                "items": [{"id": calendar_id}]
            }
            
            result = await asyncio.to_thread(service.freebusy().query(body=body).execute)
            calendars = result.get("calendars", {})
            cal_data = calendars.get(calendar_id, {})
            busy_list = cal_data.get("busy", [])
            
            busy_slots: list[tuple[datetime, datetime]] = []
            for busy in busy_list:
                # Normalizar Z a +00:00 para compatibilidad con python < 3.11
                start_str = busy["start"].replace("Z", "+00:00")
                end_str = busy["end"].replace("Z", "+00:00")
                busy_slots.append((
                    datetime.fromisoformat(start_str),
                    datetime.fromisoformat(end_str)
                ))
            return busy_slots
        except Exception as exc:
            logger.warning("Failed to query Google Calendar freebusy: %s. Falling back to empty busy slots.", exc)
            return []

    async def create_event(self, draft: CalendarEventDraft) -> str:
        """
        Crea un evento en Google Calendar usando un borrador y devuelve el ID del evento creado.
        Si la integración está inactiva, simula la creación del evento de forma controlada.
        """
        if not self.google_cal.enabled:
            logger.info("Google Calendar integration is disabled. Simulating event creation.")
            return "mock-event-id-12345"

        try:
            service = self.google_cal._build_service()
            calendar_id = self.google_cal.settings.google_calendar_id

            event: dict[str, Any] = {
                "summary": draft.title,
                "start": {"dateTime": draft.start_time},
                "end": {"dateTime": draft.end_time},
            }
            if draft.location:
                event["location"] = draft.location
            if draft.description:
                event["description"] = draft.description
            if draft.attendees:
                event["attendees"] = [{"email": email} for email in draft.attendees]

            created = await asyncio.to_thread(
                service.events()
                .insert(calendarId=calendar_id, body=event)
                .execute
            )
            return created.get("id", "google-event-id")
        except Exception as exc:
            logger.error("Could not create event in Google Calendar: %s", exc)
            raise GoogleCalendarServiceError("Could not create Google Calendar event.") from exc
