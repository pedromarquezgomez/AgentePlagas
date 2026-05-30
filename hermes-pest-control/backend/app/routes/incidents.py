from fastapi import APIRouter, HTTPException, Query, status

from app.services.incident_service import IncidentNotFoundError, IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])
incident_service = IncidentService()


@router.get("")
async def list_incidents(
    status: str | None = None,
    priority: str | None = None,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await incident_service.list_incidents(
        status_filter=status,
        priority=priority,
        limit=limit,
    )


@router.get("/{incident_id}")
async def get_incident(incident_id: str) -> dict:
    try:
        return await incident_service.get_incident(incident_id)
    except IncidentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        ) from exc
