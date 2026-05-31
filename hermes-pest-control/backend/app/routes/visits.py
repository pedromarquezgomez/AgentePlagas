from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.schemas.visit import VisitCreate, VisitUpdate
from app.services.google_calendar_service import (
    GoogleCalendarService,
    GoogleCalendarServiceError,
)
from app.services.visit_service import VisitNotFoundError, VisitService

router = APIRouter(
    prefix="/visits",
    tags=["visits"],
    dependencies=[Depends(require_admin_auth)],
)
visit_service = VisitService()
google_calendar_service = GoogleCalendarService()


@router.get("")
async def list_visits(
    incident_id: str | None = None,
    technician_id: str | None = None,
    status: str | None = None,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await visit_service.list_visits(
        incident_id=incident_id,
        technician_id=technician_id,
        status_filter=status,
        limit=limit,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_visit(visit_create: VisitCreate) -> dict:
    visit = await visit_service.create_visit(visit_create)
    return visit.model_dump()


@router.post("/{visit_id}/sync-calendar")
async def sync_visit_calendar(visit_id: str) -> dict:
    try:
        visit = await visit_service.get_visit(visit_id)
    except VisitNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found.",
        ) from exc

    if not google_calendar_service.enabled:
        return {
            "status": "skipped",
            "reason": "google_calendar_disabled",
            "visit": visit,
        }

    try:
        event_id = visit.get("external_calendar_event_id")
        if event_id:
            event = await google_calendar_service.update_event_for_visit(
                visit,
                event_id,
            )
        else:
            event = await google_calendar_service.create_event_for_visit(visit)

        updates = {
            "external_calendar_provider": google_calendar_service.provider,
            "external_calendar_event_id": event.get("id", event_id),
            "external_calendar_sync_status": "synced",
            "external_calendar_last_synced_at": datetime.now(timezone.utc),
            "external_calendar_error": None,
        }
        updated_visit = await visit_service.update_visit(visit_id, updates)
        return {"status": "synced", "visit": updated_visit}
    except GoogleCalendarServiceError as exc:
        updates = {
            "external_calendar_provider": google_calendar_service.provider,
            "external_calendar_sync_status": "failed",
            "external_calendar_last_synced_at": datetime.now(timezone.utc),
            "external_calendar_error": str(exc),
        }
        updated_visit = await visit_service.update_visit(visit_id, updates)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "status": "failed",
                "reason": "google_calendar_sync_failed",
                "visit": updated_visit,
            },
        ) from exc


@router.get("/{visit_id}")
async def get_visit(visit_id: str) -> dict:
    try:
        return await visit_service.get_visit(visit_id)
    except VisitNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found.",
        ) from exc


@router.patch("/{visit_id}")
async def update_visit(
    visit_id: str,
    visit_update: VisitUpdate,
) -> dict:
    updates = visit_update.model_dump(exclude_unset=True)
    try:
        return await visit_service.update_visit(visit_id, updates)
    except VisitNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found.",
        ) from exc
