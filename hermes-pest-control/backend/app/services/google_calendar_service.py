import json
from typing import Any

from app.config.settings import Settings, settings


class GoogleCalendarServiceError(RuntimeError):
    pass


class GoogleCalendarService:
    provider = "google"

    def __init__(self, settings_obj: Settings | None = None) -> None:
        self.settings = settings_obj or settings

    @property
    def enabled(self) -> bool:
        return self.settings.google_calendar_enabled

    async def create_event_for_visit(self, visit: dict) -> dict:
        service = self._build_service()
        event = self._event_payload_for_visit(visit)
        try:
            return (
                service.events()
                .insert(calendarId=self.settings.google_calendar_id, body=event)
                .execute()
            )
        except Exception as exc:
            raise GoogleCalendarServiceError("Could not create Google Calendar event.") from exc

    async def update_event_for_visit(self, visit: dict, event_id: str) -> dict:
        service = self._build_service()
        event = self._event_payload_for_visit(visit)
        try:
            return (
                service.events()
                .update(
                    calendarId=self.settings.google_calendar_id,
                    eventId=event_id,
                    body=event,
                )
                .execute()
            )
        except Exception as exc:
            raise GoogleCalendarServiceError("Could not update Google Calendar event.") from exc

    async def get_event(self, event_id: str) -> dict:
        service = self._build_service()
        try:
            return (
                service.events()
                .get(calendarId=self.settings.google_calendar_id, eventId=event_id)
                .execute()
            )
        except Exception as exc:
            raise GoogleCalendarServiceError("Could not get Google Calendar event.") from exc

    async def delete_event(self, event_id: str) -> dict:
        service = self._build_service()
        try:
            service.events().delete(
                calendarId=self.settings.google_calendar_id,
                eventId=event_id,
            ).execute()
            return {"status": "deleted", "event_id": event_id}
        except Exception as exc:
            raise GoogleCalendarServiceError("Could not delete Google Calendar event.") from exc

    def _build_service(self) -> Any:
        if not self.enabled:
            raise GoogleCalendarServiceError("Google Calendar integration is disabled.")
        if not self.settings.google_calendar_id:
            raise GoogleCalendarServiceError("GOOGLE_CALENDAR_ID is not configured.")

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            scopes = ["https://www.googleapis.com/auth/calendar.events"]
            if self.settings.google_calendar_credentials_json:
                info = json.loads(self.settings.google_calendar_credentials_json)
                credentials = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=scopes,
                )
            elif self.settings.google_calendar_credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self.settings.google_calendar_credentials_path,
                    scopes=scopes,
                )
            else:
                raise GoogleCalendarServiceError(
                    "Google Calendar credentials are not configured."
                )

            import httplib2
            http = httplib2.Http(timeout=4)
            return build("calendar", "v3", credentials=credentials, http=http, cache_discovery=False)
        except GoogleCalendarServiceError:
            raise
        except Exception as exc:
            raise GoogleCalendarServiceError(
                "Could not initialize Google Calendar client."
            ) from exc

    def _event_payload_for_visit(self, visit: dict) -> dict:
        summary = f"Hermes visita incidencia {visit.get('incident_id')}"
        description_parts = []
        if visit.get("notes"):
            description_parts.append(str(visit["notes"]))
        if visit.get("technician_id"):
            description_parts.append(f"Técnico: {visit['technician_id']}")

        event: dict[str, Any] = {
            "summary": summary,
            "description": "\n".join(description_parts),
        }
        if visit.get("address"):
            event["location"] = visit["address"]
        if visit.get("scheduled_start"):
            event["start"] = {"dateTime": str(visit["scheduled_start"])}
        if visit.get("scheduled_end"):
            event["end"] = {"dateTime": str(visit["scheduled_end"])}
        elif visit.get("scheduled_start"):
            event["end"] = {"dateTime": str(visit["scheduled_start"])}
        return event
