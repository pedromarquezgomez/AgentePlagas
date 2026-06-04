from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.services.visit_service import VisitService

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
    dependencies=[Depends(require_admin_auth)],
)
visit_service = VisitService()


@router.get("/status")
async def get_calendar_status() -> dict:
    from app.services.google_calendar_service import GoogleCalendarService
    from app.config.settings import settings
    from datetime import datetime, timezone, timedelta

    enabled = settings.google_calendar_enabled
    calendar_id = settings.google_calendar_id
    auth_type = "none"
    if settings.google_calendar_credentials_json or settings.google_calendar_credentials_path:
        auth_type = "service_account"

    can_read = False
    can_write = False

    if enabled:
        try:
            gcal = GoogleCalendarService()
            service = gcal._build_service()
            now_iso = datetime.now(timezone.utc).isoformat()
            later_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

            body = {
                "timeMin": now_iso,
                "timeMax": later_iso,
                "items": [{"id": calendar_id}]
            }
            service.freebusy().query(body=body).execute()
            can_read = True
        except Exception:
            pass

        if can_read:
            try:
                event_body = {
                    "summary": "Hermes Status Test Event",
                    "start": {"dateTime": now_iso},
                    "end": {"dateTime": later_iso},
                }
                created = (
                    service.events()
                    .insert(calendarId=calendar_id, body=event_body)
                    .execute()
                )
                event_id = created.get("id")
                if event_id:
                    can_write = True
                    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            except Exception:
                pass

    return {
        "calendar_enabled": enabled,
        "provider": "google_calendar",
        "authentication": auth_type,
        "calendar_id": calendar_id,
        "can_read": can_read,
        "can_write": can_write
    }


@router.get("/visits")
async def list_calendar_visits(
    start_date: date,
    end_date: date,
    technician_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[dict]:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be greater than or equal to start_date.",
        )

    return await visit_service.list_calendar_visits(
        start_date=start_date,
        end_date=end_date,
        technician_id=technician_id,
        status_filter=status_filter,
    )


@router.post("/optimize-route")
async def optimize_route(
    payload: dict,
) -> dict:
    technician_id = payload.get("technician_id")
    date_str = payload.get("date")
    apply = payload.get("apply", False)

    if not technician_id or not date_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="technician_id and date are required.",
        )

    try:
        visit_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format, use YYYY-MM-DD.",
        )

    from app.calendar.optimizer import RouteOptimizer
    optimizer = RouteOptimizer()
    return await optimizer.optimize_route(
        technician_id=technician_id,
        visit_date=visit_date,
        apply=apply,
    )
